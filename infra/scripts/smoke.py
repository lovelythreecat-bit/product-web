"""Small GET-only health probe. No credentials, mutations or Agent requests."""

import argparse
import json
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    try:
        url = urlsplit(args.base_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in {"", "/"}
        ):
            raise ValueError("invalid_origin")
        result = {}
        for name in ("live", "ready"):
            with build_opener(NoRedirect).open(
                args.base_url.rstrip("/") + "/api/v1/health/" + name, timeout=5
            ) as response:
                data = json.loads(response.read(16384))
                result[name] = response.status == 200 and data.get(name) is True
        print(json.dumps({"ok": all(result.values()), "checks": result}))
        return 0 if all(result.values()) else 2
    except Exception:
        print('{"ok":false,"code":"health_probe_failed"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
