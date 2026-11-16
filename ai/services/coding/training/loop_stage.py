"""Training wiring for the agent-loop model: ONE model trained on the approved multi-turn trajectories of real dev-agent tasks (coding_agent/traj_review.jsonl),
with the same WSL trainer/export/Ollama-registration machinery as every other local model (stage.py). It continues from your recovery model's own adapter, NOT from
the single-turn coding_agent model (which answered in one turn and so failed inside the agent), and registers the result under its own name, "<base>-coding_agent_loop".
Its config is coding_agent/agent_loop_training.json: min_traces (the approval gate) is the same 40 as for the other coding model. Never switches the model in Settings."""

from __future__ import annotations

from typing import Callable

from ai.services.coding import AGENT_DIR
from ai.services.coding.training import stage

CONFIG_PATH = str(AGENT_DIR / "agent_loop_training.json")

TOO_FEW_HINT = ("Too few approved agent-loop trajectories to train on. Run the dev agent on more real tasks (scripts/traj_run.ps1), then review "
                 "coding_agent/traj_review.jsonl and approve more (python scripts/ledger_train.py --mode loop --stages extract refreshes it).")


def train_config():
    return stage.train_config(cfg_path=CONFIG_PATH)


def names(current_model: str) -> tuple[str, str]:
    """(model to compare against - your recovery model unless the config says otherwise, the new agent-loop model)."""
    cfg = train_config()
    original, new_model = stage.names(current_model, cfg)
    return cfg.best_model or original, cfg.new_model or new_model


def run(train_file: str, current_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    return stage.run(train_file, current_model, dry_run=dry_run, fresh=fresh, log=log, cfg_path=CONFIG_PATH,
                     example_label="approved agent-loop trajectories", too_few_hint=TOO_FEW_HINT)
