"""A stand-in ComfyUI for tests: a real separate process that speaks the part of ComfyUI's HTTP API WealthFlow uses.

  python fake_comfy_server.py --port N [--delay SECONDS] [--exit-code C] [--host H]
--delay waits before listening (a server that is still loading); --exit-code prints an error and exits (a server that crashes)."""

import argparse
import base64
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body: bytes, ctype="application/json", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(json.dumps(data).encode(), code=code)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/system_stats":
            self._json({"system": {"os": "fake"}, "devices": []})
        elif path.startswith("/object_info/"):
            cls = path.rsplit("/", 1)[-1]
            self._json({cls: {"input": {"required": {}}}})
        elif path.startswith("/history/"):
            pid = path.rsplit("/", 1)[-1]
            self._json({pid: {"status": {"completed": True, "status_str": "success"}, "outputs": {"13": {"images": [{"filename": "o.png", "subfolder": "", "type": "output"}]}}}})
        elif path == "/view":
            self._send(PNG, "image/png")
        else:
            self._json({}, 404)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/prompt":
            self._json({"prompt_id": "p1"})
        elif self.path == "/upload/image":
            self._json({"name": "up.png", "subfolder": ""})
        elif self.path == "/free":
            self._json({})
        else:
            self._json({}, 404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--delay", type=float, default=0)
    ap.add_argument("--exit-code", type=int, default=None)
    a = ap.parse_args()
    if a.exit_code is not None:
        print("boom: cannot load model", flush=True)
        sys.exit(a.exit_code)
    print("fake comfy loading", flush=True)
    time.sleep(a.delay)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
