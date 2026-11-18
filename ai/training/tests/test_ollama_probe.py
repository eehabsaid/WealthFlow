"""The preflight Ollama check must never hang the training command (a stuck `ollama show` used to block it for 30+ minutes)."""

import subprocess
import unittest
from unittest.mock import patch

from ai.training.services import preflight


class OllamaProbeTest(unittest.TestCase):
    def test_no_output_pipes_and_a_short_timeout(self):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0)

        with patch.object(preflight.subprocess, "run", fake_run):
            self.assertTrue(preflight._ollama_has("m"))
        self.assertNotIn("capture_output", seen)
        self.assertEqual((seen["stdout"], seen["stderr"], seen["stdin"]), (subprocess.DEVNULL,) * 3)
        self.assertLessEqual(seen["timeout"], 30)

    def test_timeout_missing_binary_and_nonzero_exit_mean_not_available(self):
        for outcome in (subprocess.TimeoutExpired("ollama", 30), FileNotFoundError(), subprocess.CompletedProcess([], 1)):
            def fake_run(cmd, _o=outcome, **kwargs):
                if isinstance(_o, Exception):
                    raise _o
                return _o

            with patch.object(preflight.subprocess, "run", fake_run):
                self.assertFalse(preflight._ollama_has("m"))
