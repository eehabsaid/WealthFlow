"""Per-request pipeline trace: what each stage produced, how long it took, how many LLM calls it made.

Logged at WARNING level on purpose — the project has no LOGGING config, so INFO is
hidden (same reason [AI-TIMING] lines in ollama_provider use WARNING). Grep for
"[AI-PIPELINE]" next to "[AI-TIMING]" to see stage wall-clock alongside model timing.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger("core.ai.pipeline")

STAGES = ("understand", "retrieve", "reason", "tool", "validate", "respond")
_MAX_DETAIL_CHARS = 700


@dataclass
class StageRecord:
    name: str
    status: str = "ok"                       # ok | skipped | error
    duration_ms: int = 0
    detail: dict[str, Any] = field(default_factory=dict)
    llm_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.name, "status": self.status, "duration_ms": self.duration_ms,
            "llm_calls": len(self.llm_calls), "llm_ms": sum(c["ms"] for c in self.llm_calls),
            "detail": self.detail,
        }


class PipelineTrace:
    def __init__(self, user_id: Any = None, conversation_id: Any = None):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.started = time.monotonic()
        self.records: dict[str, StageRecord] = {}
        self._current: StageRecord | None = None

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    @contextmanager
    def stage(self, name: str) -> Iterator[StageRecord]:
        rec = StageRecord(name)
        self._current = rec
        t0 = time.monotonic()
        try:
            yield rec
        except Exception as exc:
            rec.status = "error"
            rec.detail["error"] = f"{type(exc).__name__}: {exc}"[:300]
            raise
        finally:
            rec.duration_ms = int((time.monotonic() - t0) * 1000)
            self.records[name] = rec
            self._current = None
            self._log(rec)

    def skip(self, name: str, reason: str) -> StageRecord:
        rec = StageRecord(name, status="skipped", detail={"reason": reason})
        self.records[name] = rec
        self._log(rec)
        return rec

    def skip_remaining(self, reason: str) -> None:
        for name in STAGES:
            if name not in self.records:
                self.skip(name, reason)

    def record_llm_call(self, ms: int, prompt_tokens: Any, completion_tokens: Any, error: Any) -> None:
        if self._current is not None:
            self._current.llm_calls.append({
                "ms": ms, "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, "error": bool(error),
            })

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ms": self.elapsed_ms(),
            "stages": [self.records[n].to_dict() for n in STAGES if n in self.records],
        }

    def _prefix(self) -> str:
        return f"[AI-PIPELINE] user={self.user_id} conv={self.conversation_id}"

    def _log(self, rec: StageRecord) -> None:
        detail = json.dumps(rec.detail, default=str, ensure_ascii=False)
        if len(detail) > _MAX_DETAIL_CHARS:
            detail = detail[:_MAX_DETAIL_CHARS] + "…"
        logger.warning(
            "%s stage=%s status=%s ms=%d llm_calls=%d detail=%s",
            self._prefix(), rec.name, rec.status, rec.duration_ms, len(rec.llm_calls), detail,
        )

    def log_summary(self) -> None:
        parts = " ".join(
            f"{n}={self.records[n].duration_ms}ms{'(skip)' if self.records[n].status == 'skipped' else ''}"
            for n in STAGES if n in self.records
        )
        logger.warning("%s summary total=%dms %s", self._prefix(), self.elapsed_ms(), parts)


class TracedProvider:
    """Transparent proxy: forwards everything to the real provider and records each
    generate() call (wall-clock + token counts) against the currently running stage."""

    def __init__(self, provider: Any, trace: PipelineTrace):
        self._provider = provider
        self._trace = trace

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        t0 = time.monotonic()
        res = self._provider.generate(*args, **kwargs)
        info = res if isinstance(res, dict) else {}
        self._trace.record_llm_call(
            int((time.monotonic() - t0) * 1000),
            info.get("prompt_tokens"), info.get("completion_tokens"), info.get("error"),
        )
        return res
