"""Phase 3 of the coding-agent plan, in ONE command (`python scripts/agent_train.py`): a verified coding dataset built from this repo's own git
history (9), a coding-only fine-tune of the original model kept apart from the business training (10), and an evaluation on held-out real
changes (11). It never switches the model in Settings. Settings: coding_agent/training.json (edit it; nothing is hardcoded here)."""

from __future__ import annotations

import json

from ai.services.coding import AGENT_DIR


def settings(name: str = "training.json") -> dict:
    """`name` picks which settings file under coding_agent/ to load: the git-history coding dataset uses "training.json" (the default, unchanged);
    the ledger-based example types each get their own file ("qa_training.json", "patch_training.json")."""
    return json.loads((AGENT_DIR / name).read_text(encoding="utf-8"))
