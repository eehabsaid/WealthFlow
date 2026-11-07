"""Helpers: a real server on a free 127.0.0.1 port with a fake model, and a tiny HTTP client."""

import json
import threading
import time
import urllib.error
import urllib.request

from ..server.app import build

TOKEN = "t" * 40


class MemStore:
    backend = "memory (tests)"
    _cached = None

    def __init__(self):
        self.data = {}

    def get(self, name):
        return self.data.get(name)

    def set(self, name, value):
        self.data[name] = value
        return "memory"

    def delete(self, name):
        self.data.pop(name, None)


class Api:
    def __init__(self, repo, *providers, web_dir=None):
        queue = list(providers)
        factory = lambda settings: queue.pop(0) if len(queue) > 1 else queue[0]   # noqa: E731
        self.store = MemStore()
        self.server = build(repo, TOKEN, 0, store=self.store, provider_factory=factory, web_dir=web_dir)
        self.port = self.server.port
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def call(self, method, path, body=None, token=TOKEN, headers=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        head = {"Authorization": f"Bearer {token}"} if token else {}
        if data is not None:
            head["Content-Type"] = ctype
        head.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=head)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def json(self, method, path, body=None, **kw):
        status, data, _ = self.call(method, path, body, **kw)
        return status, (json.loads(data) if data[:1] in (b"{", b"[") else data)

    def wait_idle(self, timeout=20):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if not self.json("GET", "/api/state")[1]["busy"]:
                return True
            time.sleep(0.05)
        return False

    def close(self):
        self.server.service.shutdown()
        self.server.shutdown()
        self.server.server_close()
