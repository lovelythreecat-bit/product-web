"""No ambient proxies or secondary DNS: connect to approved numeric IP, preserve TLS host."""

import http.client
import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass
from queue import Empty, Queue
from threading import BoundedSemaphore, Thread, Timer
from urllib.parse import urljoin, urlsplit


class DownloadRejected(ValueError):
    pass


class OriginalUnavailable(DownloadRejected):
    pass


@dataclass(frozen=True)
class DownloadPolicy:
    allowed_download_sources: tuple[str, ...]
    max_download_bytes: int
    max_total_bytes: int
    download_timeout_seconds: float
    max_redirects: int

    def __post_init__(self):
        if any(
            type(v) is not int
            for v in (self.max_download_bytes, self.max_total_bytes, self.max_redirects)
        ):
            raise DownloadRejected("Download limits require integers")
        object.__setattr__(self, "allowed_download_sources", tuple(self.allowed_download_sources))
        if (
            not self.allowed_download_sources
            or self.max_download_bytes <= 0
            or self.max_total_bytes <= 0
            or not 0 < self.download_timeout_seconds <= 300
            or not 0 <= self.max_redirects <= 10
        ):
            raise DownloadRejected("Invalid exact download policy")


@dataclass(frozen=True)
class ApprovedTarget:
    url: str
    scheme: str
    host: str
    port: int
    ips: tuple[str, ...]

    def check_peer(self, peer):
        if str(ipaddress.ip_address(peer)) not in self.ips:
            raise DownloadRejected("Connection IP mismatch")


def resolve(host, port):
    return [row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def origin(url):
    try:
        parts = urlsplit(url)
        if (
            parts.scheme not in {"https", "http"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
            or len(url) > 2048
            or "\\" in url
            or any(ord(c) <= 32 or ord(c) == 127 for c in url)
            or "%" in parts.netloc
        ):
            raise ValueError()
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port or (443 if parts.scheme == "https" else 80)
        # Explicit origins still cannot authorize non-HTTP service ports.
        if port not in {80, 443}:
            raise ValueError()
        return parts.scheme, host, port
    except (ValueError, UnicodeError):
        raise DownloadRejected("Unapproved result URL") from None


def validate_result_url(url, source_policy, dns=resolve):
    sources = (
        source_policy.allowed_download_sources
        if isinstance(source_policy, DownloadPolicy)
        else source_policy
    )
    wanted = origin(url)
    approved = set()
    for source in sources:
        if source == "TEST_ONLY:bound-mock":
            continue  # This token never approves a network origin.
        parsed = urlsplit(source)
        if parsed.path not in {"", "/"} or parsed.query:
            raise DownloadRejected("Policy must name an exact origin")
        approved.add(origin(source))
    if wanted not in approved:
        raise DownloadRejected("Source not approved")
    scheme, host, port = wanted
    addresses = dns(host, port)
    ips = []
    try:
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if (
                not ip.is_global
                or ip.is_multicast
                or ip.is_unspecified
                or isinstance(ip, ipaddress.IPv6Address)
                and (
                    ip.ipv4_mapped is not None or ip.sixtofour is not None or ip.teredo is not None
                )
            ):
                raise ValueError()
            ips.append(str(ip))
    except ValueError:
        raise DownloadRejected("Unsafe DNS answer") from None
    if not ips:
        raise DownloadRejected("No approved address")
    return ApprovedTarget(url, scheme, host, port, tuple(dict.fromkeys(ips)))


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DownloadRejected("Download deadline")
    return remaining


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, target, timeout):
        super().__init__(target.host, target.port, timeout=timeout)
        self.target = target
        self.deadline = time.monotonic() + timeout
        self._active_socket = None

    def _use_socket(self, sock):
        # Publish before any blocking operation. A deadline firing while TLS
        # detaches the raw fd is also caught before starting the handshake.
        self.sock = self._active_socket = sock
        sock.settimeout(_remaining(self.deadline))

    def connect(self):
        target = self.target
        ip = target.ips[0]
        sock = socket.socket(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._use_socket(sock)
            sock.connect((ip, target.port))  # numeric only: never resolves target.host again
            sock.settimeout(_remaining(self.deadline))
            target.check_peer(sock.getpeername()[0])
            if target.scheme == "https":
                context = ssl.create_default_context()
                sock.settimeout(_remaining(self.deadline))
                sock = context.wrap_socket(
                    sock, server_hostname=target.host, do_handshake_on_connect=False
                )
                self._use_socket(sock)
                sock.do_handshake()
                sock.settimeout(_remaining(self.deadline))
                target.check_peer(sock.getpeername()[0])
        except BaseException:
            self.close()
            raise

    def send(self, data):
        # HTTPConnection.request reaches this before both connect and sendall.
        if self.sock is None:
            if not self.auto_open:
                raise http.client.NotConnected()
            self.connect()
        self.sock.settimeout(_remaining(self.deadline))
        super().send(data)
        _remaining(self.deadline)


_DNS_SLOTS = BoundedSemaphore(16)


def _bounded_dns(dns, host, port, deadline):
    if not _DNS_SLOTS.acquire(blocking=False):
        raise DownloadRejected("DNS capacity")
    result = Queue(maxsize=1)

    def run():
        try:
            result.put((True, dns(host, port)))
        except Exception:
            result.put((False, None))
        finally:
            _DNS_SLOTS.release()

    Thread(target=run, daemon=True).start()
    try:
        ok, addresses = result.get(timeout=max(0, deadline - time.monotonic()))
    except Empty:
        raise DownloadRejected("DNS deadline") from None
    if not ok:
        raise DownloadRejected("DNS unavailable")
    return addresses


def _interrupt_connection(connection):
    # Keep the active socket even when HTTPResponse owns it after getresponse.
    # PinnedConnection updates this reference for both raw TCP and wrapped TLS.
    sock = getattr(connection, "_active_socket", None) or getattr(connection, "sock", None)
    if sock is not None:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def download_chunks(url, policy, *, dns=resolve, connection_factory=PinnedConnection):
    """Streaming bytes, fixed total deadline, each redirect revalidated before connection."""
    deadline = time.monotonic() + policy.download_timeout_seconds
    count = 0
    for hop in range(policy.max_redirects + 1):
        target = validate_result_url(
            url, policy, lambda host, port: _bounded_dns(dns, host, port, deadline)
        )
        connection = connection_factory(target, _remaining(deadline))
        connection.deadline = deadline  # One budget, including DNS and every redirect.
        watchdog = Timer(_remaining(deadline), _interrupt_connection, (connection,))
        watchdog.daemon = True
        watchdog.start()  # Covers request's TCP connect, TLS handshake and sendall.
        try:
            parts = urlsplit(url)
            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            connection.request("GET", path, headers={"Accept-Encoding": "identity"})
            sock = getattr(connection, "sock", None)
            if sock is not None:
                connection._active_socket = sock
                sock.settimeout(_remaining(deadline))
            _remaining(deadline)
            response = connection.getresponse()
            _remaining(deadline)
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location or hop == policy.max_redirects:
                    raise DownloadRejected("Redirect limit")
                url = urljoin(url, location)
                continue
            if response.status in {403, 404, 410}:
                raise OriginalUnavailable("Original link unavailable")
            if response.status != 200 or response.getheader("Content-Encoding") not in {
                None,
                "identity",
            }:
                raise DownloadRejected("Invalid result response")
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isdigit() or int(length) > policy.max_download_bytes
            ):
                raise DownloadRejected("Download size")
            while True:
                remaining = _remaining(deadline)
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                # read1 bounds each blocking call; read(n) may loop on a slow trickle.
                chunk = response.read1(min(65536, policy.max_download_bytes - count + 1))
                _remaining(deadline)
                if not chunk:
                    break
                count += len(chunk)
                if count > policy.max_download_bytes:
                    raise DownloadRejected("Download size")
                yield chunk
            if count == 0 or length is not None and count != int(length):
                raise DownloadRejected("Incomplete result response")
            return
        finally:
            watchdog.cancel()
            connection.close()
    raise DownloadRejected("Redirect limit")
