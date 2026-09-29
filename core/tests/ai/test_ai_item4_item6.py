"""Backlog item 4 (deterministic prefetch on the default path) and item 6 (entity grounding)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from core.views.ai_chat.chat_pipeline import PipelineTrace
from core.views.ai_chat.chat_pipeline.entity_check import check_entities
from core.views.ai_chat.chat_pipeline.prefetch import run_prefetch
from core.views.ai_chat.chat_pipeline.reason import run_reason
from core.views.ai_chat.chat_pipeline.retrieve import Retrieval
from core.views.ai_chat.chat_pipeline.validate import _full_report

D = "business_data_analysis"
PF = "core.views.ai_chat.chat_pipeline.prefetch"


def U(periods=("2026-05",), topics=("expenses",), intent="data_lookup"):
    return SimpleNamespace(intent=intent, question_domain=D, topics=list(topics), entities={"periods": list(periods)})


def R(ctx='{"year":2026,"month":9}'):
    return Retrieval(messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "q"}], sources=["expenses"], context_text=ctx)


class PrefetchTest(TestCase):
    def run_pf(self, retrieval, understanding, audit, result):
        with patch(f"{PF}.validate_and_execute_tool", return_value=(audit, result)) as ex:
            out = run_prefetch(PipelineTrace(1, 1), retrieval, understanding, "expenses May 2026", SimpleNamespace(id=1))
        return out, ex

    def test_uncovered_month_runs_tool_and_appends_step0(self):
        r = R()
        out, ex = self.run_pf(r, U(), {"status": "success", "duration_ms": 5}, {"expenses": {"total": 1}})
        self.assertTrue(out.used)
        ex.assert_called_once()
        self.assertEqual(ex.call_args[0][0], "query_application_data")
        self.assertTrue(r.messages[-1]["content"].startswith("STEP 0"))
        self.assertTrue(out.executed[0]["prefetch"])

    def test_covered_month_or_other_reasons_do_not_prefetch(self):
        for r, u in ((R(), U(periods=["2026-09"])), (R(), U(intent="forecast")), (R(""), U())):
            out, ex = self.run_pf(r, u, {"status": "success"}, {"a": 1})
            self.assertFalse(out.used)
            ex.assert_not_called()

    def test_failure_falls_back_to_tools(self):
        r = R()
        out, _ = self.run_pf(r, U(), {"status": "failed"}, {})
        self.assertFalse(out.used)
        self.assertEqual(len(r.messages), 2)

    def test_reason_after_prefetch_offers_no_tools(self):
        calls = []

        def fake(provider, msgs, dom, offer_tools=True):
            calls.append(offer_tools)
            return None, None, "answer", []

        with patch("core.views.ai_chat.ai_chat_core_views.generation_pipeline.initial_generate", side_effect=fake):
            run_reason(PipelineTrace(1, 1), None, [], D, R(), U(), prefetched=True)
            run_reason(PipelineTrace(1, 1), None, [], D, R(), U(), prefetched=False)
        self.assertEqual(calls, [False, True])


class EntityCheckTest(TestCase):
    EV = '{"year":2026,"month":9,"total":"EGP 100"} "date":"2026-08-15"'

    def test_unknown_month_flagged_known_and_asked_ok(self):
        self.assertEqual(check_entities("In July 2026 you spent more", "how much", self.EV)[1], ["month 2026-07"])
        self.assertEqual(check_entities("Sept 2026 was 100", "how much", self.EV)[1], [])
        self.assertEqual(check_entities("August 2026 was 100", "how much", self.EV)[1], [])
        self.assertEqual(check_entities("In July 2026 you spent", "and July 2026?", self.EV)[1], [])

    def test_currency_only_checked_when_evidence_uses_codes(self):
        self.assertEqual(check_entities("You have 5 USD", "q", self.EV)[1], ["currency USD"])
        self.assertEqual(check_entities("You have 5 EGP", "q", self.EV)[1], [])
        self.assertEqual(check_entities("You have 5 USD", "q", '{"total":"100"}')[1], [])

    def test_merged_report(self):
        rep = _full_report("Total 100 EGP in July 2026", "q", self.EV)
        self.assertEqual(rep.ungrounded, ("month 2026-07",))
        self.assertFalse(rep.ok)
        self.assertTrue(_full_report("Total 100 EGP", "q", self.EV).ok)
