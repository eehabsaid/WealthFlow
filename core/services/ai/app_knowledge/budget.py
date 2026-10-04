"""Prompt/time budget for the reasoning path, and the "slow model" memory.

On weak hardware one model call can take minutes. After a call times out for a model, the next 30 minutes use the
compact budget (fewer chunks, shorter answer, shorter timeout) for that model name, so the user is not made to wait
five minutes again. A successful call clears it. Switching the model changes the cache key, so it resets by itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache

SLOW_TTL_S = 30 * 60


@dataclass(frozen=True)
class Budget:
    name: str
    max_chunks: int
    max_chars: int
    max_tokens: int
    timeout_s: int
    history_messages: int


def normal(max_tokens: int, timeout_s: int) -> Budget:
    return Budget("normal", 4, 2400, max_tokens, timeout_s, 4)


def compact(max_tokens: int, timeout_s: int) -> Budget:
    return Budget("compact", 2, 1000, min(max_tokens, 140), min(timeout_s, 120), 0)


def _key(model: str) -> str:
    return f"ai_workflow_slow:{(model or '').strip().lower()}"


def is_slow(model: str) -> bool:
    return bool(cache.get(_key(model)))


def mark_slow(model: str) -> None:
    cache.set(_key(model), 1, SLOW_TTL_S)


def clear_slow(model: str) -> None:
    cache.delete(_key(model))


def choose(model: str, max_tokens: int, timeout_s: int) -> Budget:
    return compact(max_tokens, timeout_s) if is_slow(model) else normal(max_tokens, timeout_s)
