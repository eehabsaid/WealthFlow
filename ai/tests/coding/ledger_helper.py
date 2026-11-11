"""Throw-away coding_agent/ tree used by the ledger-training tests: real Project/Ledger objects, isolated from the real repo's own task history
and its real coding_agent/ files (every module that resolves coding_agent/ paths for itself is redirected to the temp tree)."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.dev_agent.core.project import Project
from ai.dev_agent.ledger.ledger import Ledger
from ai.services.coding import config as coding_config
from ai.services.coding import training as coding_training
from ai.services.coding.training import ledger_examples, ledger_review

CONFIG = {"protected": [{"pattern": "app/money.py", "reason": "balances"}], "test_areas": {"app": "app/tests/test_x.py"}}
REAL_AGENT_DIR = coding_training.AGENT_DIR


class LedgerRepo(SimpleTestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        agent_dir = self.root / "coding_agent"
        agent_dir.mkdir()
        (agent_dir / "config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
        for name in ("qa_training.json", "patch_training.json"):
            shutil.copy(REAL_AGENT_DIR / name, agent_dir / name)
        for target in (coding_config, coding_training, ledger_review):
            patcher = patch.object(target, "AGENT_DIR", agent_dir)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(ledger_examples, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.project = Project(self.root)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def patch_task(self, goal: str, changes: dict[str, tuple[str | None, str]], verified: bool = True) -> Ledger:
        """`changes`: {rel: (before_or_None, after)}. Writes `after` to disk, snapshots `before`, freezes the diff, and marks the task completed
        with a final verification matching `verified` - exactly the sequence the real agent follows."""
        ledger = Ledger.create(self.project, goal)
        for rel, (before, after) in changes.items():
            ledger.snapshot_original(rel, before.encode("utf-8") if before is not None else None)
            self.write(rel, after)
            ledger.record_file(rel, "written", "before-sha", "after-sha")
        ledger.add_verification("final", [{"step": "tests", "status": "PASSED" if verified else "FAILED", "detail": ""}])
        ledger.freeze_result_diffs()
        ledger.set_status("completed")
        return ledger

    def qa_task(self, goal: str, answer: str) -> Ledger:
        ledger = Ledger.create(self.project, goal)
        ledger.data["answer"] = answer
        ledger.set_status("answered")
        ledger.save()
        return ledger

    def patch_cfg(self) -> dict:
        return ledger_examples.config("patch")

    def qa_cfg(self) -> dict:
        return ledger_examples.config("qa")
