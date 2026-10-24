"""A tiny fake Ollama HTTP server (stdlib only; no Django, no core imports) for tests and scripted browser runs.

It implements what core/integrations/ai_provider/ollama_*.py really calls: GET /api/version, GET /api/tags, POST /api/chat
(non-streaming, as the provider sends stream=false), plus /api/show and /api/ps for the runtime-capability probe. Like the real
Ollama it serves ONE chat request at a time (the others queue on a lock). Replies are scripted: a queue of replies, else a handler.

It proves routing, payloads (think on/off, tools, options), JSON / tool-call parsing, timeouts, files and UI. It does NOT prove the
quality of real qwen3.x output or real timings (`delay` only simulates slowness).

    python tests/support/fake_ollama.py [port]     # standalone, for the browser E2E run
"""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "qwen3.8:27b"
CONTEXT = 98304


def reply(content: str = "", thinking: str = "", tool_calls: list | None = None, done_reason: str = "stop", tokens: int | None = None,
          delay: float = 0.0, inline_think: str = "") -> dict:
    """One scripted answer. `thinking` goes to the separate message field, `inline_think` as <think>..</think> inside the content."""
    return {"content": (f"<think>{inline_think}</think>" if inline_think else "") + content, "thinking": thinking, "tool_calls": tool_calls,
            "done_reason": done_reason, "tokens": tokens, "delay": delay}


def tool_call(name: str, **arguments) -> dict:
    return {"function": {"name": name, "arguments": arguments}}


# The classifier / translation behaviours the app has to survive.
def yes(): return reply("YES")
def no(): return reply("No.")
def arabic_yes(): return reply("نعم")
def empty(): return reply("")
def gibberish(): return reply("¯\\_(ツ)_/¯ maybe?? " * 3)
def with_thinking(answer: str = "YES"): return reply(answer, thinking="The user asks for the app's documentation, so the answer is yes.")
def truncated(partial: str = "## Half a chapt"): return reply(partial, done_reason="length", tokens=32768)
def echo_english(chunk: str): return reply(chunk)                      # a "translation" that is the English source again
def arabic_translation(): return reply("## الفصل الأول\n\nهذا الفصل يشرح الشاشة خطوة بخطوة.\n")
def slow(content: str, seconds: float): return reply(content, delay=seconds)


class FakeOllama:
    def __init__(self, handler=None, replies: list | None = None, model: str = MODEL):
        self.handler, self.replies, self.model = handler, list(replies or []), model
        self.requests: list[dict] = []          # every /api/chat request: payload, think, tools, options, queued
        self._lock, self._meta, self._busy = threading.Lock(), threading.Lock(), 0
        self._server: ThreadingHTTPServer | None = None
        self.url = ""

    # --- life cycle -------------------------------------------------------------------------------------------------------
    def start(self, port: int = 0) -> "FakeOllama":
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):   # quiet
                pass

            def _send(self, code: int, body: dict):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):   # the client gave up (its timeout): nothing to deliver
                    pass

            def do_GET(self):
                self._send(*outer.get(self.path))

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    return self._send(400, {"error": "invalid json"})
                self._send(*outer.post(self.path, payload))

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def __enter__(self): return self.start()
    def __exit__(self, *exc): self.stop()

    # --- endpoints --------------------------------------------------------------------------------------------------------
    def get(self, path: str) -> tuple[int, dict]:
        if path.startswith("/api/version"):
            return 200, {"version": "0.12.0"}
        if path.startswith("/api/tags"):
            return 200, {"models": [{"name": self.model, "model": self.model, "size": 17_000_000_000, "details": {"parameter_size": "27B"}}]}
        if path.startswith("/api/ps"):
            return 200, {"models": []}
        return 404, {"error": "not found"}

    def post(self, path: str, payload: dict) -> tuple[int, dict]:
        if path.startswith("/api/show"):
            return 200, {"details": {"parameter_size": "27B", "family": "qwen3"}, "model_info": {"qwen3.context_length": CONTEXT}, "capabilities": ["completion", "tools", "thinking"]}
        if not path.startswith("/api/chat"):
            return 404, {"error": "not found"}
        with self._meta:
            queued = self._busy > 0
            self._busy += 1
        try:
            with self._lock:   # one request at a time, like Ollama's queue
                self.requests.append({"payload": payload, "think": payload.get("think"), "tools": bool(payload.get("tools")), "options": payload.get("options") or {},
                                      "queued": queued, "system": next((m.get("content", "") for m in payload.get("messages", []) if m.get("role") == "system"), ""),
                                      "last_user": next((m.get("content", "") for m in reversed(payload.get("messages", [])) if m.get("role") == "user"), ""),
                                      "started": time.monotonic()})
                scripted = self.replies.pop(0) if self.replies else (self.handler(payload) if self.handler else reply("OK"))
                if scripted.get("delay"):
                    time.sleep(scripted["delay"])
                self.requests[-1]["finished"] = time.monotonic()
                return 200, self._body(scripted)
        finally:
            with self._meta:
                self._busy -= 1

    def _body(self, r: dict) -> dict:
        message = {"role": "assistant", "content": r["content"]}
        if r.get("thinking"):
            message["thinking"] = r["thinking"]
        if r.get("tool_calls"):
            message["tool_calls"] = r["tool_calls"]
        tokens = r.get("tokens") or max(1, len(r["content"]) // 4)
        return {"model": self.model, "created_at": "2026-10-24T09:00:00Z", "message": message, "done": True, "done_reason": r.get("done_reason", "stop"),
                "total_duration": int(5e9), "load_duration": int(1e8), "prompt_eval_count": 800, "prompt_eval_duration": int(3e8),
                "eval_count": tokens, "eval_duration": int(tokens / 62 * 1e9)}

    # --- inspection -------------------------------------------------------------------------------------------------------
    def think_flags(self) -> list:
        return [r["think"] for r in self.requests]

    def overlapping(self) -> bool:
        """True when two chat requests were ever processed at the same time (must be False: Ollama serves one at a time)."""
        spans = sorted((r["started"], r.get("finished", r["started"])) for r in self.requests)
        return any(b[0] < a[1] for a, b in zip(spans, spans[1:]))


if __name__ == "__main__":
    server = FakeOllama(handler=lambda payload: reply("YES")).start(int(sys.argv[1]) if len(sys.argv) > 1 else 11435)
    print(server.url, flush=True)
    threading.Event().wait()
