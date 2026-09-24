"""Staged chat pipeline for the DEFAULT AI chat path.

Understand -> Retrieve -> Reason -> Tool -> Validate -> Respond, one module per stage:

- understand.py   stage 1 (new)   intent / entities / scope, deterministic
- retrieve.py     stage 2         wraps the existing context builder (logic unchanged)
- reason.py       stage 3         the existing first LLM call
- tool.py         stage 4         the existing tool-investigation loop
- validate.py     stage 5 (new)   answer-vs-evidence check (+ optional single regenerate)
- respond.py      stage 6         the existing finalize_success
- grounding.py    numeric grounding used by Validate / Understand
- trace.py        PipelineTrace + TracedProvider ([AI-PIPELINE] logs)
- runner.py       wires stages 2-6 together

Not used by the optional multi-agent orchestrator path.
"""

from .runner import run_default_pipeline
from .trace import STAGES, PipelineTrace
from .understand import Understanding, understand
from .validate import Validation, run_validate

__all__ = [
    "STAGES", "PipelineTrace", "Understanding", "Validation",
    "run_default_pipeline", "run_validate", "understand",
]
