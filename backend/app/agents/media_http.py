"""Bound-origin, bounded synchronous transport shared by media adapters and admin."""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from pydantic import SecretStr

from app.agents.text import NoRedirects, TextAgentProfile


class MediaServiceError(Exception):
    def __init__(self, status_code=503, public_message=None, *, error_code=None,
                 retry_after_seconds=None, resource_id=None, retryable_rejection=False):
        super().__init__(public_message or "媒体服务暂不可用")
        self.status_code = status_code
        self.public_message = public_message
        self.error_code = error_code
        self.retry_after_seconds = retry_after_seconds
        self.resource_id = resource_id
        self.retryable_rejection = retryable_rejection


class MediaClient:
    def __init__(self, base_url, service_key, timeout=30, max_response_bytes=8 * 1024 * 1024):
        try:
            self.base_url = TextAgentProfile.valid_url(base_url)
            key = service_key if isinstance(service_key, SecretStr) else SecretStr(service_key)
            self.service_key = TextAgentProfile.valid_key(key)
            if not 0 < timeout <= 600 or not 0 < max_response_bytes <= 1024 * 1024 * 1024:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise MediaServiceError() from None
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

    def _url(self, path):
        try:
            parts = urlsplit(path)
            decoded = unquote(parts.path)
            if (
                not isinstance(path, str)
                or not path.startswith("/")
                or path.startswith("//")
                or parts.scheme
                or parts.netloc
                or parts.fragment
                or any(ord(c) <= 32 or ord(c) >= 127 for c in path)
                or "\\" in path
                or "\\" in decoded
                or "%" in decoded
                or any(p in {".", ".."} for p in decoded.split("/"))
                or re.search(r"%2f|%5c", parts.path, re.I)
            ):
                raise ValueError()
            return self.base_url + path
        except (TypeError, ValueError):
            raise MediaServiceError() from None

    def _request(self, method, path, *, data=None, content_type=None, idempotency_key=None):
        headers = {
            "Authorization": "Bearer " + self.service_key.get_secret_value(),
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if idempotency_key is not None:
            if (
                not isinstance(idempotency_key, str)
                or not 1 <= len(idempotency_key) <= 128
                or any(not 33 <= ord(c) <= 126 for c in idempotency_key)
            ):
                raise MediaServiceError(422)
            headers["Idempotency-Key"] = idempotency_key
        if method not in {"GET", "POST", "PATCH"}:
            raise MediaServiceError(422)
        request = Request(self._url(path), data=data, method=method, headers=headers)
        try:
            opener = build_opener(ProxyHandler({}), NoRedirects())
            try:
                response = opener.open(request, timeout=self.timeout)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                # Partial content is never a complete result; redirects never carry keys onward.
                if not 200 <= status < 300 or status == 206:
                    error_code, resource_id, retry_after = None, None, None
                    rejected = False
                    if status == 429:
                        try:
                            retry_after = max(1, min(3600, int(
                                response.headers.get("Retry-After", "5"))))
                        except (ValueError, TypeError):
                            retry_after = 5
                        raw_error = response.read(min(self.max_response_bytes, 65536) + 1)
                        try:
                            payload = json.loads(raw_error) if len(raw_error) <= 65536 else None
                            if isinstance(payload, dict):
                                error_code = payload.get("code")
                                resources = [payload.get(k) for k in (
                                    "task_id", "record_id", "generation_id", "resource_id",
                                )]
                                resource_id = next((v for v in resources if v is not None), None)
                                rejected = error_code == "queue_full" and resource_id is None
                        except (ValueError, TypeError):
                            pass
                    message = {
                        401: "媒体服务访问 Key 无效，请检查服务连接中的访问 Key。",
                        403: "媒体服务拒绝管理操作，请在服务连接中配置有效的管理 Key。",
                        413: "素材超过媒体服务的文件大小限制，请减小文件后重新提交。",
                    }.get(status)
                    raise MediaServiceError(
                        {404: 404, 409: 409, 412: 409, 413: 413, 422: 422, 429: 429}.get(
                            status, 503
                        ),
                        public_message=message,
                        error_code=error_code if error_code == "queue_full" else None,
                        retry_after_seconds=retry_after, resource_id=resource_id,
                        retryable_rejection=rejected,
                    )
                length = response.headers.get("Content-Length")
                if length is not None and int(length) > self.max_response_bytes:
                    raise MediaServiceError()
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes or (
                    length is not None and len(raw) != int(length)
                ):
                    raise MediaServiceError()
                return status, raw, response.headers.get("Content-Type", "")
        except (URLError, OSError, ValueError, TypeError):
            raise MediaServiceError() from None

    def json(self, method, path, body=None, idempotency_key=None):
        try:
            data = None if body is None else json.dumps(body, allow_nan=False).encode()
            status, raw, _ = self._request(
                method,
                path,
                data=data,
                content_type="application/json",
                idempotency_key=idempotency_key,
            )
            payload = json.loads(raw)
            if not isinstance(payload, (dict, list)):
                raise ValueError()
            return status, payload
        except (ValueError, TypeError):
            raise MediaServiceError() from None

    def upload(self, path, data, mime, fields=None):
        extensions = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/mp4": "m4a",
        }
        if mime not in extensions or not isinstance(data, bytes) or not data:
            raise MediaServiceError(422)
        boundary = "media-" + uuid4().hex
        chunks = []
        for name, value in (fields or {}).items():
            if (
                not re.fullmatch(r"[a-zA-Z0-9_]{1,64}", name)
                or not isinstance(value, str)
                or len(value) > 4096
                or "\r" in value
                or "\n" in value
                or name == "file"
            ):
                raise MediaServiceError(422)
            chunks.append(
                (
                    f"--{boundary}\r\nContent-Disposition: form-data; "
                    f'name="{name}"\r\n\r\n{value}\r\n'
                ).encode()
            )
        chunks.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="file"; filename="upload.{extensions[mime]}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode()
        )
        chunks += [data, f"\r\n--{boundary}--\r\n".encode()]
        _, raw, _ = self._request(
            "POST",
            path,
            data=b"".join(chunks),
            content_type="multipart/form-data; boundary=" + boundary,
        )
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError()
            return payload
        except (ValueError, TypeError):
            raise MediaServiceError() from None

    def download(self, path):
        _, raw, content_type = self._request("GET", path)
        return raw, content_type.split(";", 1)[0].strip().lower()
