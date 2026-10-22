"""Server-only client for the text service's model configuration API."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from app.agents.text import NoRedirects, TextAgentProfile


class TextModelService(BaseModel):
    # Management can be configured before the first generation model exists.
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    base_url: str
    service_key: SecretStr

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        return TextAgentProfile.valid_url(value)

    @field_validator("service_key")
    @classmethod
    def valid_key(cls, value):
        return TextAgentProfile.valid_key(value)


class TextModelError(Exception):
    def __init__(self, status_code=503, *, public_message=None):
        self.status_code = status_code
        self.public_message = public_message


class TextModelClient:
    def __init__(self, service):
        if service is None:
            raise TextModelError()
        self.service = service

    def request(self, method, path="", *, config=None, revision=None, cursor=None, limit=20):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.service.service_key.get_secret_value(),
        }
        if revision is not None:
            headers["If-Match"] = f'"{revision}"'
        data = None
        if config is not None:
            body = config.model_dump(mode="python", exclude_unset=True)
            if isinstance(body.get("api_key"), SecretStr):
                body["api_key"] = body["api_key"].get_secret_value()
            data = json.dumps(body, allow_nan=False).encode()
        query = ""
        if method == "GET" and not path:
            query = "?" + urlencode({"limit": limit, **({"cursor": cursor} if cursor else {})})
        request = Request(
            self.service.base_url + "/v1/model-configs" + path + query,
            data=data,
            method=method,
            headers=headers,
        )
        try:
            opener = build_opener(ProxyHandler({}), NoRedirects())
            try:
                response = opener.open(request, timeout=15)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                if status not in {200, 201}:
                    if status == 401:
                        raise TextModelError(public_message=(
                            "文本服务访问 Key 无效或已被吊销，请在「配置服务连接」中更新"
                            "由 textAgent 签发的服务访问 Key；模型密钥应填写在模型配置中。"
                        ))
                    if status == 403:
                        raise TextModelError(public_message=(
                            "文本服务访问 Key 权限不足，请在「配置服务连接」中使用具有 "
                            "configs:read 和 configs:write 权限的服务访问 Key。"
                        ))
                    raise TextModelError({412: 409, 404: 404, 422: 422, 429: 429}.get(status, 503))
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise TextModelError()
            return json.loads(raw)
        except (URLError, OSError, ValueError):
            raise TextModelError() from None
