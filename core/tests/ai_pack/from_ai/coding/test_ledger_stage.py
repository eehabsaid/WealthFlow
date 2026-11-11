"""Training wiring for the ledger-based coding_agent model: one combined model, continuing from recovery's own adapter, registering as
"<base>-coding_agent" - never a name containing "recovery" - and never training below the config's own minimum."""

import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services.coding.training import ledger_stage


class NamesTests(SimpleTestCase):
    def test_the_configured_best_and_new_model_names_are_used_as_is(self):
        cfg = ledger_stage.train_config()
        best, new = ledger_stage.names("whatever-is-in-settings-right-now")
        self.assertEqual(best, cfg.best_model)
        self.assertEqual(new, cfg.new_model)

    def test_the_new_model_name_never_contains_the_word_recovery(self):
        _, new = ledger_stage.names("qwen3.8:27b-recovery")
        self.assertNotIn("recovery", new)
        self.assertTrue(new.endswith("coding_agent"))

    def test_whatever_model_is_currently_selected_in_settings_does_not_change_the_result(self):
        # the config pins original/best/new explicitly, so the currently-selected model must not leak into the computed names
        a = ledger_stage.names("qwen3.8:27b-150k")
        b = ledger_stage.names("some-other-model-entirely")
        self.assertEqual(a, b)


class RunGateTests(SimpleTestCase):
    def test_too_few_approved_examples_blocks_training_before_anything_starts(self):
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"messages": []}\n')
        logged = []
        with patch("ai.training.services.wsl.stream") as stream:
            out = ledger_stage.run(path, "qwen3.8:27b-recovery", log=logged.append)
        self.assertEqual(out["status"], "blocked")
        stream.assert_not_called()
        self.assertTrue(any("approved QA + patch examples" in line and "FIX" in line for line in logged), logged)
