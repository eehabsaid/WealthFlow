"""Test environment for the front ends (browser and VS Code extension tests): a throw-away project plus a fake Ollama server that answers from a script.

    python -m dev_agent.tests.fake_env <project_dir> <script.json>

script.json is a list; each item is a reply string (sent as the model's answer) or {"hang": true} (never answers, like a model that is still thinking).
Prints one JSON line {"project": ..., "ollama_port": ...} when ready and runs until killed. The real `python -m dev_agent serve` is then started
against that project, so the real provider adapter, server and engine are all exercised; only the model's answers are fake."""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .conftest import CONFIG, FILES


def make_project(root: Path, port: int) -> None:
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    (root / "tests" / "test_slow.py").write_text("import time\n\n\ndef test_slow():\n    time.sleep(120)\n", encoding="utf-8")
    (root / "coding_agent").mkdir(exist_ok=True)
    (root / "coding_agent" / "config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    settings = {"provider": "ollama", "model": "fake", "providers": {"ollama": {"base_url": f"http://127.0.0.1:{port}"}}}
    (root / "coding_agent" / "agent_settings.json").write_text(json.dumps(settings), encoding="utf-8")


def serve(script: list) -> ThreadingHTTPServer:
    lock, state = threading.Lock(), {"n": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, data):
            raw = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self._json({"models": [{"name": "fake"}, {"name": "fake-2"}]})

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.path.endswith("/api/show"):   # the vision check: a model whose name contains "vision" reports the capability; no script reply is used
                name = json.loads(body or b"{}").get("model", "")
                return self._json({"capabilities": ["completion", "vision"] if "vision" in name else ["completion"]})
            with lock:
                item = script[min(state["n"], len(script) - 1)] if script else ""
                state["n"] += 1
            if isinstance(item, dict) and item.get("hang"):
                time.sleep(600)
            self._json({"message": {"content": item}, "prompt_eval_count": 10, "eval_count": 5})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    return server


def main() -> None:
    root, script = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    server = serve(script)
    make_project(root, server.server_address[1])
    print(json.dumps({"project": str(root), "ollama_port": server.server_address[1]}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
