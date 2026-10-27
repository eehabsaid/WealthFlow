"""The user's real question through the real chat endpoint, Agent mode, the real OllamaProvider and the fake Ollama server.

The scripted model behaves like a good agent: it searches the screen data, reads the endpoint with the date from the question, and
writes the answer from the tool result. The pipeline (tools, limits, guards, sources) is the real one; real qwen is not involved."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.models import AppSettings
from core.services.ai.agent import set_chat_mode
from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import compute_custom_cash_projection
from core.tests.billing.test_support import grant_ai_workspace_access
from tests.support import fake_ollama as fo

from ..test_chat_domains import GP, VIEW
from .support import TARGET, TODAY, tenant

CASH = "/api/financial-advisor/cash-flow-custom-projection/"
QUESTION = f"based on the Cash Projection how much cash will I have on {TARGET.isoformat()}? EGP only"
CTX = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": QUESTION}], [])


def tool_results(payload: dict) -> list[dict]:
    out = []
    for m in payload["messages"]:
        if m.get("role") == "tool":
            try:
                out.append(json.loads(m["content"]))
            except ValueError:
                out.append({"raw": m["content"]})
    return out


def good_agent(payload: dict) -> dict:
    results = tool_results(payload)
    if not results:
        return fo.reply("", tool_calls=[fo.tool_call("app_screen_data", search="cash flow projection")])
    last = results[-1]
    if "matches" in last:
        path = next(m["path"] for m in last["matches"] if "custom-projection" in m["path"])
        return fo.reply("", tool_calls=[fo.tool_call("app_screen_data", path=path, query={"target_date": TARGET.isoformat()})])
    data = last["data"]
    lines = [f"- {e['date']} {e['type']}: {e['amount']:,.2f}" for e in data["included_events"]]
    return fo.reply(f"Projected EGP cash on {data['target_date']}: {data['projected_balance']:,.2f}\n" + "\n".join(lines))


class AgentReadsTheScreenTest(TestCase):
    handler = staticmethod(good_agent)

    def setUp(self):
        self.user = tenant("sd_chat_user", "200000")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        for key, value in (("ai_enabled", "true"), ("ai_direct_answers", "false"), ("ai_agent_enabled", "true"),
                           ("ai_domain_business", "true"), ("ai_domain_app", "false")):   # the same settings as the real install
            AppSettings.set(key, value)
        set_chat_mode(self.user, "agent")
        self.server = fo.FakeOllama(handler=self.handler).start()
        self.addCleanup(self.server.stop)
        self.provider = OllamaProvider(base_url=self.server.url, model=fo.MODEL, timeout=60)

    def ask(self, text: str = QUESTION) -> dict:
        with patch(f"{VIEW}.get_active_ai_provider", return_value=self.provider), patch(GP, return_value=CTX), \
                self.assertLogs("core.ai.pipeline", level="WARNING"):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_the_answer_carries_the_cash_flow_pages_number_and_events(self):
        data = self.ask()
        shown = compute_custom_cash_projection(self.user, TODAY, TARGET)
        content = data["message"]["content"]
        self.assertIn(f"{shown['projected_balance']:,.2f}", content)
        self.assertTrue(any(e["type"] == "certificate_maturity" for e in shown["included_events"]))
        for event in shown["included_events"]:   # future dates and amounts are not stripped by the answer guards
            self.assertIn(f"{event['date']} {event['type']}: {event['amount']:,.2f}", content)

    def test_the_model_was_offered_the_tool_and_told_to_use_it_first(self):
        self.ask()
        first = self.server.requests[0]
        names = [t["function"]["name"] for t in first["payload"]["tools"]]
        self.assertIn("app_screen_data", names)
        self.assertNotIn("app_read_file", names)   # business domain: no code tools
        self.assertIn("app_screen_data", first["system"])
        self.assertIn("Never rebuild such a figure by hand", first["system"])

    def test_steps_and_sources_come_from_the_calls_that_really_ran(self):
        data = self.ask()
        self.assertEqual([c["tool"] for c in data["message"]["tool_calls"]], ["app_screen_data", "app_screen_data"])
        self.assertIn("investigation_data", data["sources"])
        self.assertIn(f"agent:screen:{CASH}", data["sources"])
        self.assertEqual(len(self.server.requests), 3)   # search, read, answer: no hand-made estimate, no instant answer

    def test_the_other_user_gets_their_own_number(self):
        other = tenant("sd_chat_other", "90000")
        self.client.force_login(other)
        grant_ai_workspace_access(other)
        set_chat_mode(other, "agent")
        content = self.ask()["message"]["content"]   # the screen's own interest update runs first, so compare afterwards
        self.assertIn(f"{compute_custom_cash_projection(other, TODAY, TARGET)['projected_balance']:,.2f}", content)


class ModelStartsWithAWrongPathTest(AgentReadsTheScreenTest):
    """A model that guesses an endpoint gets a helpful message and recovers by searching."""

    @staticmethod
    def handler(payload: dict) -> dict:
        results = tool_results(payload)
        if not results:
            return fo.reply("", tool_calls=[fo.tool_call("app_screen_data", path="/api/cashflow/projection/")])
        if "error" in results[-1] and len(results) == 1:
            assert "search" in results[-1]["error"]
            return fo.reply("", tool_calls=[fo.tool_call("app_screen_data", search="cash flow projection")])
        return good_agent(payload)

    def test_steps_and_sources_come_from_the_calls_that_really_ran(self):
        data = self.ask()
        self.assertEqual(len(data["message"]["tool_calls"]), 3)
        self.assertIn(f"{compute_custom_cash_projection(self.user, TODAY, TARGET)['projected_balance']:,.2f}", data["message"]["content"])


class QuickFiguresPointToTheScreenToolTest(TestCase):
    def test_a_quick_figure_result_reminds_the_model_to_read_the_screen_for_projections(self):
        from core.services.ai.investigation import app_tools

        user = tenant("sd_quick", "200000")
        out = app_tools.computed_figures(user, {"question": "what is my net worth"})
        if out.get("figures"):
            self.assertIn("app_screen_data", out["note"])
