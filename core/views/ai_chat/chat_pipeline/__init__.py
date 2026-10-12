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
- workflow.py     how/where/should questions: knowledge chunks + approved examples, one LLM call, no data snapshot
- investigate.py  the investigator: explores code / the user's data / docs with read-only tools; takes over when a normal path gives up

Not used by the optional multi-agent orchestrator path.
"""

from .investigate import ESCALATE, escalating, run_investigator_pipeline, should_go_direct
from .runner import run_default_pipeline
from .trace import STAGES, PipelineTrace
from .understand import Understanding, understand
from .validate import Validation, run_validate
from .workflow import run_workflow_pipeline, workflow_enabled

__all__ = [
    "ESCALATE", "STAGES", "PipelineTrace", "Understanding", "Validation",
    "escalating", "run_default_pipeline", "run_investigator_pipeline", "run_validate", "should_go_direct", "run_workflow_pipeline", "understand", "workflow_enabled",
]
