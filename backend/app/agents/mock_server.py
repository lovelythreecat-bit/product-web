"""T01 mock shell; T03 owns the later agent protocol and fault controls."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        live = self.path == "/health/live"
        payload = (
            {"live": True, "mode": "mock", "test_only": True, "capabilities": []}
            if live
            else {"error": "NOT_IMPLEMENTED", "test_only": True}
        )
        body = json.dumps(payload).encode()
        self.send_response(200 if live else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if os.getenv("APP_MODE") != "mock" or os.getenv("APP_TEST_ONLY") != "true":
        raise SystemExit("Mock shell requires mock mode and TEST_ONLY=true")
    ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
