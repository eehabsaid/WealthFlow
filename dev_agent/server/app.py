"""The local HTTP server. Binds 127.0.0.1 only (exclusive on Windows), every /api request needs the bearer token, Host and Origin are checked,
bodies are size-limited JSON, errors never leak internals. The web UI is served from the same origin; the VS Code extension talks to the same API."""

from __future__ import annotations

import json
import socket
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..core.project import PathError
from ..engine.attachments import AttachmentError
from ..providers.base import ProviderError
from ..providers.registry import build_provider
from ..service import diffs
from ..service.keys import Keys
from ..service.tasks import ServiceError, TaskService
from ..settings.secrets import SecretsError
from ..settings.store import Settings, SettingsError
from . import auth, routes_misc, routes_tasks, static
from .http import HttpError, Req, Resp, Stream

MAX_BODY = 1_000_000
MAX_TASK_BODY = 22_000_000   # POST /api/tasks may carry attachments (up to 5 images of 3 MB as base64, plus text files)
ROUTES = routes_tasks.ROUTES + routes_misc.ROUTES
SERVICE_STATUS = {"not_found": 404, "conflict": 409, "busy": 409, "bad_request": 400}


def _error_for(exc: Exception) -> HttpError:
    if isinstance(exc, HttpError):
        return exc
    if isinstance(exc, ServiceError):
        return HttpError(SERVICE_STATUS.get(exc.code, 400), exc.code, str(exc))
    if isinstance(exc, SecretsError):
        locked = str(exc) == "passphrase_required"
        return HttpError(423 if locked else 400, "passphrase_required" if locked else "secrets", str(exc))
    if isinstance(exc, AttachmentError):
        return HttpError(400, "attachments", str(exc))
    if isinstance(exc, ProviderError):
        return HttpError(400, "provider", str(exc))
    if isinstance(exc, SettingsError):
        return HttpError(400, "settings", str(exc))
    if isinstance(exc, diffs.NotInTask) or isinstance(exc, FileNotFoundError):
        return HttpError(404, "not_found", "not found")
    if isinstance(exc, PathError):
        return HttpError(400, "bad_request", str(exc))
    print(f"[dev_agent server] internal error: {type(exc).__name__}", file=sys.stderr)
    return HttpError(500, "internal", "internal error")


class Handler(BaseHTTPRequestHandler):
    server_version, sys_version, timeout = "DevAgent", "", 30

    def log_message(self, *args):   # headers (the token) are never logged; requests are not logged at all unless the server was started verbose
        if self.server.verbose:
            print("[dev_agent server]", args[0] % args[1:] if len(args) > 1 else args[0], file=sys.stderr)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def _handle(self, method: str) -> None:
        try:
            result = self._dispatch(method)
        except Exception as exc:
            err = _error_for(exc)
            result = Resp({"error": str(err), "code": err.code}, err.status)
        try:
            self._send(result)
        except (OSError, ValueError):
            pass   # the client went away

    def _dispatch(self, method: str):
        split, port = urllib.parse.urlsplit(self.path), self.server.port
        if not auth.host_ok(self.headers.get("Host"), port):
            raise HttpError(403, "forbidden", "bad Host header")
        if not auth.origin_ok(self.headers.get("Origin"), self.headers.get("Sec-Fetch-Site"), port):
            raise HttpError(403, "forbidden", "cross-site request refused")
        if not split.path.startswith("/api/"):
            if method != "GET":
                raise HttpError(405, "bad_request", "method not allowed")
            return static.serve(split.path, self.server.web_dir)
        if not auth.request_ok(self.server.token, self.headers, port):
            raise HttpError(401, "unauthorized", "missing or wrong access token")
        body = self._body(method, split.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(split.query).items()}
        known = False
        for route_method, rx, fn in ROUTES:
            found = rx.fullmatch(split.path)
            if found:
                known = True
                if route_method == method:
                    return fn(Req(self.server, method, split.path, found, query, body, self.headers))
        raise HttpError(405 if known else 404, "not_found", "no such endpoint")

    def _body(self, method: str, path: str = ""):
        if method not in ("POST", "PUT", "DELETE"):
            return None
        if self.headers.get("Transfer-Encoding"):
            raise HttpError(411, "bad_request", "send a Content-Length")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HttpError(400, "bad_request", "bad Content-Length") from None
        if length > (MAX_TASK_BODY if path == "/api/tasks" else MAX_BODY) or length < 0:
            raise HttpError(413, "too_large", "request body too large")
        if length == 0:
            return None
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            raise HttpError(415, "bad_request", "send application/json")
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HttpError(400, "bad_request", "invalid JSON") from None
        if not isinstance(body, dict):
            raise HttpError(400, "bad_request", "the body must be a JSON object")
        return body

    def _send(self, result) -> None:
        stream = result if isinstance(result, Stream) else None
        resp = result if isinstance(result, Resp) else Resp(None if stream else result)
        if stream:
            resp.status, resp.ctype = 200, "text/event-stream; charset=utf-8"
        else:
            body = resp.body
            data = body if isinstance(body, bytes) else body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(resp.status)
        for key, value in {"Content-Type": resp.ctype, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                           "Referrer-Policy": "no-referrer", "Connection": "close", **resp.headers}.items():
            self.send_header(key, value)
        if not stream:
            self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not stream:
            self.wfile.write(data)
            return
        self.close_connection = True

        def write(text: str) -> None:
            self.wfile.write(text.encode("utf-8"))
            self.wfile.flush()
        try:
            stream.run(write)
        except (OSError, ValueError):
            pass


class AgentServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, project, service, keys, token: str, port: int = 0, web_dir=None, verbose: bool = False):
        self.project, self.service, self.keys, self.token = project, service, keys, token
        self.web_dir, self.verbose, self.stopping = web_dir or static.WEB_DIR, verbose, threading.Event()
        super().__init__(("127.0.0.1", port), Handler)   # loopback only; there is no option to bind anything else
        self.port = self.server_address[1]

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):   # Windows: no other process may share or hijack the port
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def request_shutdown(self) -> None:
        threading.Thread(target=self.stop, daemon=True).start()

    def stop(self) -> None:
        self.stopping.set()
        self.service.shutdown()
        self.shutdown()


def build(project, token: str | None = None, port: int = 0, store=None, provider_factory=None, verbose: bool = False, web_dir=None) -> AgentServer:
    keys = Keys(project, store)
    service = TaskService(project, provider_factory or (lambda settings: build_provider(settings, keys)), lambda: Settings(project).load())
    return AgentServer(project, service, keys, token or auth.new_token(), port, web_dir, verbose)
