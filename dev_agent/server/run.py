"""`python -m dev_agent serve`: start the server, tell the caller the port on stdout (one JSON line), stop cleanly on Ctrl-C/SIGTERM or when the
launching process (the VS Code extension) disappears, killing any running command's whole tree."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import webbrowser

from .. import __version__
from ..tools import proctree
from . import auth
from .app import build


def watch_parent(server, parent_pid: int) -> None:
    def loop():
        while not server.stopping.is_set():
            if not proctree.pid_alive(parent_pid):
                server.stop()
                return
            time.sleep(2)
    threading.Thread(target=loop, daemon=True, name="parent-watch").start()


def serve(project, port: int = 0, parent_pid: int | None = None, open_browser: bool = False, verbose: bool = False) -> int:
    env_token = os.environ.get("DEV_AGENT_TOKEN")
    if env_token is not None and len(env_token) < 24:
        print("error: DEV_AGENT_TOKEN must be at least 24 characters", file=sys.stderr)
        return 2
    token = env_token or auth.new_token()
    try:
        server = build(project, token, port, verbose=verbose)
    except OSError as exc:
        print(f"error: cannot listen on 127.0.0.1:{port}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"event": "listening", "host": "127.0.0.1", "port": server.port, "pid": os.getpid(), "version": __version__}), flush=True)
    if not env_token:   # started by a person: give them the address (the token is in the #fragment, which is never sent over the network)
        url = f"http://127.0.0.1:{server.port}/#token={token}"
        print(f"Open this address (it contains your private access token):\n  {url}\nPress Ctrl-C to stop.", file=sys.stderr, flush=True)
        if open_browser:
            webbrowser.open(url)
    if parent_pid:
        watch_parent(server, parent_pid)
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: threading.Thread(target=server.stop, daemon=True).start())
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.service.shutdown()
        proctree.kill_all()
        server.server_close()
    return 0
