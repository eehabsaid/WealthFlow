"""Training wiring for the ledger-based coding_agent model: ONE model trained on the combined, approved QA + patch examples, reusing the exact
same WSL trainer/export/Ollama-registration machinery as the git-history coding fine-tune (stage.py, point 10) and the business Q&A training
(ai/training). Its own full config file, coding_agent/coding_agent_training.json, names the model it continues from (recovery, your current
best) and the clean name the result gets (no "recovery" in it) - see that file and ai/training/README.md. Never switches the model in Settings."""

from __future__ import annotations

from typing import Callable

from ai.services.coding import AGENT_DIR
from ai.services.coding.training import stage

CONFIG_PATH = str(AGENT_DIR / "coding_agent_training.json")

TOO_FEW_HINT = ("Too few approved QA + patch examples combined to train on. Run the dev agent on more tasks, review coding_agent/qa_review.jsonl "
                 "and coding_agent/patch_review.jsonl, and approve more (python scripts/ledger_train.py --stages extract to refresh them).")


def train_config():
    return stage.train_config(cfg_path=CONFIG_PATH)


def names(current_model: str) -> tuple[str, str]:
    """(best model to compare against - your recovery model unless the config says otherwise, new coding_agent model)."""
    cfg = train_config()
    original, new_model = stage.names(current_model, cfg)
    return cfg.best_model or original, cfg.new_model or new_model


def run(train_file: str, current_model: str, *, dry_run: bool = False, fresh: bool = False, log: Callable[[str], None] = print) -> dict:
    return stage.run(train_file, current_model, dry_run=dry_run, fresh=fresh, log=log, cfg_path=CONFIG_PATH,
                      example_label="approved QA + patch examples", too_few_hint=TOO_FEW_HINT)
