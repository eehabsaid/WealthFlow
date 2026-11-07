"""Minimal JSON-over-HTTP POST (stdlib urllib, so proxy and CA settings still apply) with retry on transient errors, credential redaction in every
error message, and cancellation: Stop closes the socket, so a model that is still generating is cut off at once."""

from __future__ import annotations

import functools
import http.client
import json
import socket
import threading
import time
import urllib.error
import urllib.request

from ..engine.cancel import Cancelled
from .base import ProviderError, redact

TRANSIENT = (408, 429, 500, 502, 503, 504)


def _abort(conn) -> None:
    """Shut the connection's socket (waits briefly if the cancel arrives while it is still connecting) so a blocked read returns."""
    for _ in range(40):
        if conn.sock is not None:
            break
        time.sleep(0.05)
    try:
        if conn.sock is not None:
            conn.sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    conn.close()


def _opener(cancel):
    removers = []

    def track(cls, host, **kw):
        conn = cls(host, **kw)
        if cancel is not None:
            removers.append(cancel.on_cancel(lambda: threading.Thread(target=_abort, args=(conn,), daemon=True).start()))
        return conn

    class Http(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(functools.partial(track, http.client.HTTPConnection), req)

    class Https(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(functools.partial(track, http.client.HTTPSConnection), req, context=self._context)

    return urllib.request.build_opener(Http, Https), removers


def _open(opener, request, timeout) -> dict:
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _call(opener, request, timeout, cancel) -> dict:
    """Run the request on a helper thread and wait in small steps, so Stop returns at once on every OS (closing a socket from another thread
    does not reliably wake a blocked read on Windows). The abandoned helper thread is a daemon and ends when its socket is closed or times out."""
    if cancel is None:
        return _open(opener, request, timeout)
    box, done = {}, threading.Event()

    def work():
        try:
            box["ok"] = _open(opener, request, timeout)
        except BaseException as exc:   # re-raised in the caller below
            box["err"] = exc
        finally:
            done.set()

    threading.Thread(target=work, daemon=True, name="model-request").start()
    while not done.wait(0.1):
        if cancel.is_set():
            raise Cancelled(cancel.reason)
    if "err" in box:
        raise box["err"]
    return box["ok"]


def post_json(url: str, headers: dict, body: dict, timeout: int, secrets=(), retries: int = 2, backoff: float = 1.0, cancel=None) -> dict:
    data = json.dumps(body).encode("utf-8")
    last = "unknown error"
    for attempt in range(retries + 1):
        if cancel is not None:
            cancel.check()
        opener, removers = _opener(cancel)
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            return _call(opener, request, timeout, cancel)
        except Cancelled:
            raise
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}"
            if exc.code not in TRANSIENT:
                break
        except ValueError:
            last = "provider returned invalid JSON"
            break
        except (OSError, http.client.HTTPException) as exc:   # URLError, timeouts, resets, and the socket we closed on Stop
            if cancel is not None and cancel.is_set():
                raise Cancelled(cancel.reason) from None
            last = f"cannot reach the provider: {exc}"
        finally:
            for remove in removers:
                remove()
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    raise ProviderError(redact(last, secrets))
