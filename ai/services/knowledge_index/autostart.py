"""Refresh the code index once in a background thread when the web server starts (no file watcher, no extra process)."""

from __future__ import annotations

import logging
import os
import sys
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


def should_start(argv: list[str] | None = None, env=None) -> bool:
    argv = sys.argv if argv is None else argv
    env = os.environ if env is None else env
    if not getattr(settings, "AI_KNOWLEDGE_AUTOSTART", True):
        return False
    first = os.path.basename(argv[0]) if argv else ""
    command = argv[1] if len(argv) > 1 else ""
    if "pytest" in first or command in ("test", "migrate", "makemigrations", "shell", "check", "collectstatic"):
        return False
    if first == "manage.py":
        return command == "runserver" and (env.get("RUN_MAIN") == "true" or "--noreload" in argv)
    return True      # WSGI / ASGI server process


def _work() -> None:
    try:
        from ai.services.knowledge_index import indexer

        logger.info("knowledge index refreshed: %s", indexer.refresh())
    except Exception:   # noqa: BLE001 - background maintenance must never affect the server
        logger.exception("knowledge index refresh failed; it will be retried on first use")


def start_background_refresh() -> threading.Thread | None:
    if not should_start():
        return None
    thread = threading.Thread(target=_work, name="knowledge-index-refresh", daemon=True)
    thread.start()
    return thread
