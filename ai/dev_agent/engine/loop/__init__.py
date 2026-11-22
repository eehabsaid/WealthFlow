"""The agent. Two ways in, one loop:
  - plan approval ON (default): read-only investigation -> plan -> the owner approves once -> the work loop (tools until done) -> checks and fixes -> report.
  - plan approval OFF (Settings > Behavior): no planning phase; the work loop starts at once and the owner is asked only before risky actions (guard/*).
The work loop is engine/session.py: the model calls tools and reads their results until it answers; then the project's checks run and failures go back to the same
conversation (at most 3 failed fix attempts on the same error)."""

from __future__ import annotations

from .support import (  # noqa: F401
    AgentError,
    _finished,
    _Veto,
)
from .planning import (  # noqa: F401
    _PlanningMixin,
)
from .working import (  # noqa: F401
    _WorkingMixin,
)
from .agent import (  # noqa: F401
    Agent,
)

__all__ = ['AgentError', '_finished', '_Veto', '_PlanningMixin', '_WorkingMixin', 'Agent']
