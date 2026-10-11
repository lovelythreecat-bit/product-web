"""SSRF policy rejects private resolution, rebinding and every redirect hop."""

import importlib.util

import pytest


def download():
    assert importlib.util.find_spec("app.storage.download"), "Safe result downloader is missing"
    from app.storage import download

    return download


@pytest.mark.parametrize(
    "url,addresses",
    [
        ("https://approved.example/a", ["127.0.0.1"]),
        ("https://approved.example/a", ["169.254.169.254"]),
        ("https://approved.example/a", ["10.0.0.1"]),
        ("https://approved.example/a", ["::1"]),
        ("https://approved.example/a", ["::ffff:127.0.0.1"]),
        ("https://approved.example/a", ["93.184.216.34", "192.168.1.1"]),
        ("https://approved.example:22/a", ["93.184.216.34"]),
        ("https://user@approved.example/a", ["93.184.216.34"]),
        ("https://approved.example/a#fragment", ["93.184.216.34"]),
        ("http://approved.example/a", ["93.184.216.34"]),
        ("https://evil.example/a", ["93.184.216.34"]),
    ],
)
def test_dns_ipv6_redirect_metadata(url, addresses):
    module = download()
    with pytest.raises(module.DownloadRejected):
        module.validate_result_url(url, ["https://approved.example:443"], lambda h, p: addresses)


def test_approved_target_is_pinned_and_checks_peer():
    module = download()
    target = module.validate_result_url(
        "https://approved.example/a",
        ["https://approved.example:443"],
        lambda h, p: ["93.184.216.34"],
    )
    assert target.ips == ("93.184.216.34",)
    target.check_peer("93.184.216.34")
    with pytest.raises(module.DownloadRejected):
        target.check_peer("127.0.0.1")


@pytest.mark.parametrize(
    "redirect",
    [
        "http://169.254.169.254/latest/meta-data/",
        "https://evil.example/a",
        "https://approved.example:22/a",
        "https://name:password@approved.example/a",
    ],
)
def test_each_redirect_revalidates_before_connect(redirect):
    module = download()
    opened = []

    class Response:
        status = 302

        def getheader(self, name):
            return redirect if name == "Location" else None

    class Connection:
        def __init__(self, target, timeout):
            opened.append(target.url)

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    policy = module.DownloadPolicy(("https://approved.example",), 100, 200, 10, 2)
    with pytest.raises(module.DownloadRejected):
        list(
            module.download_chunks(
                "https://approved.example/file",
                policy,
                dns=lambda h, p: ["93.184.216.34"],
                connection_factory=Connection,
            )
        )
    assert opened == ["https://approved.example/file"]


def test_rebinding_is_checked_on_redirect_and_never_re_resolved_on_connect(monkeypatch):
    module = download()
    answers = iter([["93.184.216.34"], ["127.0.0.1"]])
    opened = []

    class Response:
        status = 302

        def getheader(self, name):
            return "/next" if name == "Location" else None

    class Connection:
        def __init__(self, target, timeout):
            opened.append(target.ips)

        def request(self, *a, **kw):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    policy = module.DownloadPolicy(("https://approved.example",), 100, 200, 10, 2)
    with pytest.raises(module.DownloadRejected):
        list(
            module.download_chunks(
                "https://approved.example/file",
                policy,
                dns=lambda h, p: next(answers),
                connection_factory=Connection,
            )
        )
    assert opened == [("93.184.216.34",)]


def test_mock_exception_never_approves_network_localhost():
    module = download()
    with pytest.raises(module.DownloadRejected):
        module.validate_result_url(
            "http://127.0.0.1/a", ["TEST_ONLY:bound-mock"], lambda h, p: ["127.0.0.1"]
        )


def test_dns_resolution_obeys_absolute_deadline():
    import time

    module = download()

    def slow_dns(host, port):
        time.sleep(0.3)
        return ["93.184.216.34"]

    policy = module.DownloadPolicy(("https://approved.example",), 100, 200, 0.04, 0)
    started = time.monotonic()
    with pytest.raises(module.DownloadRejected):
        list(module.download_chunks("https://approved.example/a", policy, dns=slow_dns))
    assert time.monotonic() - started < 0.2, "DNS ignored total download deadline"


def test_slow_http_headers_obey_absolute_deadline():
    import http.client
    import socket
    import threading
    import time

    module = download()
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]

    def trickle():
        with server:
            peer, _ = server.accept()
            with peer:
                peer.recv(4096)
                try:
                    for byte in b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nx":
                        peer.sendall(bytes([byte]))
                        time.sleep(0.02)
                except OSError:
                    pass

    thread = threading.Thread(target=trickle, daemon=True)
    thread.start()
    policy = module.DownloadPolicy(("http://approved.example",), 100, 200, 0.06, 0)
    started = time.monotonic()
    try:
        list(
            module.download_chunks(
                "http://approved.example/a",
                policy,
                dns=lambda h, p: ["93.184.216.34"],
                connection_factory=lambda target, timeout: http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=timeout
                ),
            )
        )
    except (module.DownloadRejected, OSError, http.client.HTTPException):
        pass
    assert time.monotonic() - started < 0.35, "Slow header trickle exceeded total deadline"
    thread.join(1)


def test_pinned_tls_connect_uses_numeric_address_and_original_hostname(monkeypatch):
    module = download()
    observed = []

    class Socket:
        def settimeout(self, timeout):
            pass

        def connect(self, address):
            observed.append(("connect", address))

        def getpeername(self):
            return ("93.184.216.34", 443)

        def do_handshake(self):
            pass

        def close(self):
            pass

    class TLS:
        def wrap_socket(self, sock, server_hostname, do_handshake_on_connect=True):
            assert do_handshake_on_connect is False
            observed.append(("tls", server_hostname))
            return sock

    monkeypatch.setattr(module.socket, "socket", lambda *args: Socket())
    monkeypatch.setattr(module.ssl, "create_default_context", lambda: TLS())

    def unexpected_dns(*args, **kwargs):
        raise AssertionError("Connection re-resolved the hostname")

    monkeypatch.setattr(module.socket, "getaddrinfo", unexpected_dns)
    target = module.validate_result_url(
        "https://approved.example/a", ["https://approved.example"], lambda h, p: ["93.184.216.34"]
    )
    connection = module.PinnedConnection(target, 1)
    connection.connect()
    assert observed == [("connect", ("93.184.216.34", 443)), ("tls", "approved.example")]
    connection.close()


@pytest.mark.parametrize("length,body", [("4", b"abc"), ("3", b"abcd"), ("101", b"x")])
def test_download_bounds_stream_and_declared_length(length, body):
    import io

    module = download()

    class Response(io.BytesIO):
        status = 200

        def getheader(self, name):
            return length if name == "Content-Length" else None

    class Connection:
        sock = None

        def __init__(self, *args):
            self.response = Response(body)

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return self.response

        def close(self):
            self.response.close()

    policy = module.DownloadPolicy(("https://approved.example",), 100, 200, 1, 0)
    with pytest.raises(module.DownloadRejected):
        list(
            module.download_chunks(
                "https://approved.example/a",
                policy,
                dns=lambda h, p: ["93.184.216.34"],
                connection_factory=Connection,
            )
        )


@pytest.mark.parametrize("blocked_phase", ["tls", "send"])
def test_tcp_tls_send_share_absolute_deadline(monkeypatch, blocked_phase):
    """Real request/send/connect flow; only the OS socket and TLS engine are delayed."""
    import io
    import threading
    import time

    module = download()
    trace = []
    interrupted = threading.Event()
    budget = 0.4
    initial_timeout = None
    started = time.monotonic()

    class Socket:
        def __init__(self, phase_name="raw"):
            self.phase_name = phase_name
            self.timeout = None

        def settimeout(self, timeout):
            nonlocal initial_timeout
            self.timeout = timeout
            if initial_timeout is None:
                initial_timeout = timeout
            trace.append(("timeout", self.phase_name, round(timeout, 4)))

        def phase(self, name):
            # Each old implementation stage stays below its per-socket timeout,
            # but TCP+TLS (or TCP+TLS+send) exceeds the one download budget.
            fractions = {"connect": 0.65, "tls": 0.65, "send": 0.1}
            if blocked_phase == "send":
                fractions = {"connect": 0.3, "tls": 0.3, "send": 0.65}
            duration = initial_timeout * fractions[name]
            available = self.timeout
            canceled = interrupted.wait(min(duration, available))
            trace.append(
                (
                    name,
                    round(time.monotonic() - started, 4),
                    "planned",
                    round(duration, 4),
                    "timeout",
                    round(available, 4),
                )
            )
            if canceled:
                raise OSError("TEST_ONLY socket shutdown")
            if duration > available:
                raise TimeoutError("TEST_ONLY socket timeout")

        def connect(self, address):
            assert address == ("93.184.216.34", 443)
            self.phase("connect")

        def getpeername(self):
            return ("93.184.216.34", 443)

        def do_handshake(self):
            self.phase("tls")

        def sendall(self, data):
            assert b"Host: approved.example:443\r\n" in data
            self.phase("send")

        def shutdown(self, how):
            trace.append(("watchdog", self.phase_name, round(time.monotonic() - started, 4)))
            interrupted.set()

        def close(self):
            pass

    class TLS:
        def wrap_socket(self, sock, server_hostname, do_handshake_on_connect=True):
            assert server_hostname == "approved.example"
            wrapped = Socket("tls")
            wrapped.settimeout(sock.timeout)
            if do_handshake_on_connect:
                wrapped.do_handshake()
            return wrapped

    class Response(io.BytesIO):
        status = 200

        def getheader(self, name):
            return "1" if name == "Content-Length" else None

    class Connection(module.PinnedConnection):
        def getresponse(self):
            return Response(b"x")

    monkeypatch.setattr(module.socket, "socket", lambda *args: Socket())
    monkeypatch.setattr(module.ssl, "create_default_context", lambda: TLS())
    policy = module.DownloadPolicy(("https://approved.example",), 100, 200, budget, 0)
    with pytest.raises((module.DownloadRejected, OSError)):
        list(
            module.download_chunks(
                "https://approved.example/a",
                policy,
                dns=lambda h, p: ["93.184.216.34"],
                connection_factory=Connection,
            )
        )
    elapsed = time.monotonic() - started
    print(
        "T11_FIX1_DEADLINE",
        blocked_phase,
        "budget",
        budget,
        "elapsed",
        round(elapsed, 4),
        "trace",
        trace,
    )
    assert elapsed < budget + 0.075, "Connect/TLS/send exceeded the shared absolute deadline"
    if blocked_phase == "tls":
        assert not any(row[0] == "send" for row in trace), (
            "Send ran after handshake exhausted budget"
        )
