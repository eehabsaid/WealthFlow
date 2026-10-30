"""Shared helpers for the model-test tests: scripted answers instead of the chat path, and extra expense rows."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import patch

from ai_training.models import AgentTrace
from ai_training.services import eval_report, evaluate, ollama_ctl
from ai_training.services.config import load
from ai_training.tests.test_trace_pipeline import TraceBase
from core.models import AppSettings

OLD, NEW = "qwen3:27b", "qwen3:27b-agent"


def add_expenses(user, amounts):
    from core.models import Expense
    base = Expense.objects.filter(owner=user).order_by("date").first()
    for i, amount in enumerate(amounts):
        base.pk, base.date, base.day, base.amount, base.amount_base = None, base.date.replace(day=11 + i), 11 + i, amount, amount
        base.save()


class Base(TraceBase):
    def setUp(self):
        super().setUp()
        AppSettings.set("ai_model", OLD)
        AppSettings.set("ai_provider", "ollama")
        self.out = tempfile.mkdtemp()
        self.asked = []

    def scripted(self, good_for, crash_on=None):
        """A replacement for runner.ask: the model in Settings decides whether the answer is right (good_for) or wrong."""
        def ask(user, case, attempt, source="generated"):
            model = AppSettings.get("ai_model", "", user=None)
            self.asked.append((model, case.key, source))
            if crash_on and model == crash_on:
                raise RuntimeError("boom")
            values = [str(v) for v in case.expected["values"]]
            shown = values if model in good_for else ["999"]
            result = json.dumps({"rows": values})
            return AgentTrace.objects.create(owner=user, source=source, case_key=case.key, question=case.question, model_name=model, reason="answered",
                                             steps=[{"tool": "app_data_query", "arguments": {"model": "Expense"}, "result": result}],
                                             answer="Result: " + ", ".join(shown), expected=case.expected), ""
        return ask

    def run_eval(self, good_for=(OLD, NEW), crash_on=None, seen=None, restart=True, min_q=2):
        with patch("ai_training.services.runner.ask", side_effect=self.scripted(good_for, crash_on)), \
                patch.object(eval_report, "MIN_QUESTIONS", min_q), \
                patch.object(ollama_ctl, "restart", return_value=restart) as rs, \
                patch.object(ollama_ctl, "installed", return_value={OLD, NEW} if seen is None else seen), \
                patch("ai_training.services.evaluate.train_stage.free_gpu") as unload:
            self.restart_mock, self.unload_mock = rs, unload
            return evaluate.run(self.user, load(eval_questions=4), OLD, out_dir=self.out, log=lambda line: None)
