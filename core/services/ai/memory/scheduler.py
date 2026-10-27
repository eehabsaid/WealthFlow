"""Runs the memory writer in a background thread so the user's reply is never delayed."""

from __future__ import annotations

import logging
import sys
import threading

from django.conf import settings

logger = logging.getLogger(__name__)
_running: set[int] = set()   # users with a pass in flight: the next pass reads the same recent messages, so skipping loses nothing
_lock = threading.Lock()


def background_enabled() -> bool:
    return bool(getattr(settings, "AI_MEMORY_BACKGROUND", True)) and "pytest" not in sys.modules and sys.argv[1:2] != ["test"]


def _run(user_id: int, conversation_id: int) -> None:
    from django.contrib.auth import get_user_model
    from django.db import close_old_connections

    from core.integrations.ai_provider import get_active_ai_provider
    from core.models import AIConversation

    from .writer import update_memory

    try:
        user = get_user_model().objects.filter(pk=user_id).first()
        conversation = AIConversation.objects.filter(pk=conversation_id, user_id=user_id).first()
        if user and conversation:
            update_memory(user, conversation, get_active_ai_provider(user=user))
    except Exception:   # memory is best-effort: it must never affect the chat
        logger.exception("memory writer failed")
    finally:
        with _lock:
            _running.discard(user_id)
        close_old_connections()


def schedule_memory_update(user_id: int, conversation_id: int) -> bool:
    if not background_enabled():
        return False
    with _lock:
        if user_id in _running:
            return False
        _running.add(user_id)
    threading.Thread(target=_run, args=(user_id, conversation_id), daemon=True, name="ai-memory-writer").start()
    return True
