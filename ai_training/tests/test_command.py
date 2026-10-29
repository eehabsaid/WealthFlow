"""The single `ai_training` command end to end: questions -> real chat endpoint -> judges -> files; resume; errors."""

from __future__ import annotations

import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from ai_training.models import AgentTrace
from ai_training.tests.test_trace_pipeline import CTX, VIEW, TraceBase


class CommandTest(TraceBase):
    def call(self, *args):
        out = StringIO()
        call_command("ai_training", *args, stdout=out)
        return out.getvalue()

    def fire(self, *args, final=lambda n: "You have 3 expense records."):
        with patch(f"{VIEW}.get_active_ai_provider", return_value=self.script(final)), \
                patch(f"{VIEW}.generation_pipeline.build_context", return_value=CTX):
            return self.call("--user", "trace_user", "--out", self.folder, *args)

    def setUp(self):
        super().setUp()
        self.folder = tempfile.mkdtemp()

    def test_one_command_asks_judges_and_writes_all_three_files(self):
        text = self.fire("--limit", "2", "--seed", "1")
        self.assertIn("Using the data of: trace_user", text)
        self.assertRegex(text, r"to ask, 0 already proven")
        self.assertIn("Questions asked: 2", text)
        for name in ("agent_traces.jsonl", "agent_runs.xlsx", "report.txt"):
            self.assertTrue(os.path.exists(os.path.join(self.folder, name)), name)
        self.assertEqual(AgentTrace.objects.count(), 4)       # 2 questions x 2 asks

    def test_a_second_run_skips_proven_questions_and_asks_the_rest_again(self):
        self.fire("--limit", "1", "--seed", "1")
        proven = AgentTrace.objects.filter(verdict="kept", attempt=1).count()
        text = self.fire("--limit", "1", "--seed", "1")
        self.assertIn(f"{1 - proven} to ask, {proven} already proven", text)
        self.assertEqual(AgentTrace.objects.filter(attempt=1).count(), 1)   # nothing doubled
        self.assertIn("1 to ask, 0 already proven", self.fire("--limit", "1", "--seed", "1", "--fresh"))

    def test_default_user_is_the_first_sysadmin(self):
        from core.tests.ai.investigation.support import make_user
        make_user("the_boss", sysadmin=True)
        with patch(f"{VIEW}.get_active_ai_provider", return_value=None):
            self.assertIn("Using the data of: the_boss", self.call("--limit", "1", "--out", self.folder))

    def test_unknown_user_is_a_plain_error(self):
        with self.assertRaises(CommandError):
            self.call("--user", "nobody", "--out", self.folder)


class ResumeTest(TraceBase):
    def make(self, expected, verdict="kept"):
        return AgentTrace.objects.create(owner=self.user, case_key=self.case.key, attempt=1, question="q", expected=expected, verdict=verdict)

    def test_proven_for_the_same_data_is_skipped(self):
        from ai_training.services import pipeline
        self.make(self.case.expected)
        todo, skipped = pipeline.split_done(self.user, [self.case])
        self.assertEqual((todo, skipped, AgentTrace.objects.count()), ([], 1, 1))

    def test_changed_data_dropped_or_fresh_means_ask_again_and_old_rows_are_removed(self):
        from ai_training.services import pipeline
        for expected, verdict, fresh in (({"values": [99]}, "kept", False), (self.case.expected, "dropped", False), (self.case.expected, "kept", True)):
            AgentTrace.objects.all().delete()
            self.make(expected, verdict)
            todo, skipped = pipeline.split_done(self.user, [self.case], fresh)
            self.assertEqual((len(todo), skipped, AgentTrace.objects.count()), (1, 0, 0))
