"""Short-lived, user-scoped queue for validated voice-answer sentences."""

from __future__ import annotations

from django.core.cache import cache

_TTL_SECONDS = 600
_MAX_SENTENCES = 250
_MAX_TEXT_CHARS = 100_000


def _key(user_id: int, turn_id: str) -> str:
    return f"wf_voice_sentences:{user_id}:{turn_id}"


def begin_voice_stream(user_id: int, turn_id: str) -> None:
    cache.set(_key(user_id, turn_id), {"sentences": [], "done": False}, _TTL_SECONDS)


def publish_voice_sentence(user_id: int, turn_id: str, text: str) -> bool:
    key = _key(user_id, turn_id)
    state = cache.get(key)
    clean = str(text or "").strip()
    if not isinstance(state, dict) or state.get("done") or state.get("blocked") or not clean:
        return False
    sentences = state["sentences"]
    total = sum(len(item) for item in sentences)
    if len(sentences) >= _MAX_SENTENCES or total + len(clean) > _MAX_TEXT_CHARS:
        state["blocked"] = True
        cache.set(key, state, _TTL_SECONDS)
        return False
    sentences.append(clean)
    cache.set(key, state, _TTL_SECONDS)
    return True


def stop_voice_stream(user_id: int, turn_id: str, failed: bool = False) -> None:
    key = _key(user_id, turn_id)
    state = cache.get(key)
    if not isinstance(state, dict):
        return
    state["blocked"] = True
    state["failed"] = state.get("failed", False) or bool(failed)
    cache.set(key, state, _TTL_SECONDS)


def finish_voice_stream(user_id: int, turn_id: str, failed: bool = False) -> None:
    key = _key(user_id, turn_id)
    state = cache.get(key)
    if not isinstance(state, dict):
        state = {"sentences": []}
    state["done"] = True
    state["failed"] = state.get("failed", False) or bool(failed)
    cache.set(key, state, _TTL_SECONDS)


def read_voice_sentences(user_id: int, turn_id: str, offset: int) -> dict:
    state = cache.get(_key(user_id, turn_id))
    if not isinstance(state, dict):
        return {"sentences": [], "next": offset, "done": False, "failed": False, "blocked": False}
    sentences = state.get("sentences", [])
    page = sentences[offset : offset + 25]
    return {
        "sentences": page,
        "next": offset + len(page),
        "done": bool(state.get("done")),
        "failed": bool(state.get("failed")),
        "blocked": bool(state.get("blocked")),
    }
