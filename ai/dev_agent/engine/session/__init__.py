"""One model conversation (a phase): the model calls tools, sees the (clipped) results and goes on until it answers without a tool call (or `submit_plan` while planning).
Native tool calling (Ollama, Anthropic, OpenAI, Gemini tools APIs) is the normal path; a model that writes its call as JSON text still works (text protocol), and a server
that has no tools API is switched to it automatically. Malformed output never ends the run: the problem is fed back to the model, up to a few times in a row.
Guards against loops: the same call repeated, a step limit, the context budget (engine/budget.py)."""

from __future__ import annotations

from .results import (  # noqa: F401
    MAX_INVALID_TEXT,
    MAX_INVALID_NATIVE,
    MAX_CALLS_PER_REPLY,
    LENGTH_STOPS,
    PhaseResult,
    _brief,
    _summary,
    _context_event,
    _Empty,
)
from .handling import (  # noqa: F401
    _HandlingMixin,
)
from .conversation import (  # noqa: F401
    _Conversation,
)
from .phase import (  # noqa: F401
    run_phase,
)

__all__ = ['MAX_INVALID_TEXT', 'MAX_INVALID_NATIVE', 'MAX_CALLS_PER_REPLY', 'LENGTH_STOPS', 'PhaseResult', '_brief', '_summary', '_context_event', '_Empty', '_HandlingMixin', '_Conversation', 'run_phase']
