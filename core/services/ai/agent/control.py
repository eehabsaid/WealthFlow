"""Stop flag and live step list for a running Agent turn (in-process cache, same scope as the existing progress polling:
with several web workers a Stop click can reach another worker and is then ignored until the next step check there)."""

from __future__ import annotations

import time

from core.services.ai.cache_manager import AICacheManager

TTL_S = 1800.0
MAX_STEPS_SHOWN = 40


def _stop_key(user_id, conversation_id) -> str:
    return f"ai_loop_stop:{user_id}:{conversation_id}"


def request_stop(user, conversation_id) -> None:
    AICacheManager().set(_stop_key(user.id, conversation_id), True, ttl_seconds=TTL_S)


def is_stopped(user, conversation_id) -> bool:
    return bool(conversation_id is not None and AICacheManager().get(_stop_key(user.id, conversation_id)))


def clear_stop(user, conversation_id) -> None:
    AICacheManager().invalidate(_stop_key(user.id, conversation_id))


def publish(user, conversation_id, *, step, max_steps, tool, label, started, steps) -> None:
    """Progress state the chat polls: the current step plus the list of steps so far (label + status), like Continue's steps."""
    if conversation_id is None:
        return
    AICacheManager().set(f"ai_loop_progress:{user.id}:{conversation_id}", {
        "status": "running", "step": step, "max_steps": max_steps, "tool": tool, "label": label,
        "elapsed_s": round(time.monotonic() - started, 1), "steps": steps[-MAX_STEPS_SHOWN:], "can_stop": True,
        "started_at": time.time() - (time.monotonic() - started)}, ttl_seconds=TTL_S)
