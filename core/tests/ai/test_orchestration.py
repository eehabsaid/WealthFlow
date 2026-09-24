"""Tests for the multi-agent orchestration engine. Reachable via the
ai_multi_agent_enabled setting (AI Settings page) — see
core/services/ai/orchestration/__init__.py and
core/views/ai_chat/ai_chat_core_views/__init__.py. Uses a mocked/fake
provider throughout — never a live model call."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.services.ai.orchestration import Orchestrator, TaskState
from core.services.ai.orchestration.agents import AdvisorAgent, DataAgent, ScenarioAgent
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()


class FakeProvider:
    """Returns pre-scripted generate() responses in order, one per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate(self, messages, tools=None, **kwargs):
        self.calls.append(messages)
        content = self._responses.pop(0) if self._responses else ""
        return {"content": content, "tool_calls": None, "prompt_tokens": 1, "completion_tokens": 1, "error": None}


class OrchestratorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="orch_user", password="password123")

    def test_goal_met_on_first_decision(self):
        provider = FakeProvider(['{"goal_met": true, "final_answer": "42"}'])
        orch = Orchestrator(provider)
        state = orch.run("what is the answer?", self.user)
        self.assertEqual(state.status, "done")
        self.assertEqual(state.final_answer, "42")
        self.assertEqual(len(state.steps), 0)

    def test_one_advisor_step_then_goal_met(self):
        step1 = '{"goal_met": false, "agent": "advisor_agent", "action": "overview", "params": {}}'
        step2 = '{"goal_met": true, "final_answer": "done"}'
        provider = FakeProvider([step1, step2])
        with patch(
            "core.services.ai.orchestration.agents.advisor_agent.get_financial_advisor_payload",
            return_value={"total": 100},
        ):
            orch = Orchestrator(provider)
            state = orch.run("summarize my finances", self.user)
        self.assertEqual(state.status, "done")
        self.assertEqual(len(state.steps), 1)
        self.assertEqual(state.steps[0]["agent"], "advisor_agent")
        self.assertEqual(state.steps[0]["result"]["data"], {"total": 100})

    def test_narrated_json_still_parses(self):
        # Real production quirk (see fake_tool_call_recovery.py docstring):
        # the model sometimes narrates around the JSON instead of returning
        # it cleanly.
        narrated = 'Sure, I will check that.\n{"goal_met": true, "final_answer": "ok"}\nDone.'
        provider = FakeProvider([narrated])
        orch = Orchestrator(provider)
        state = orch.run("goal", self.user)
        self.assertEqual(state.status, "done")
        self.assertEqual(state.final_answer, "ok")

    def test_unparsable_decision_fails_cleanly(self):
        provider = FakeProvider(["not json at all"])
        orch = Orchestrator(provider)
        state = orch.run("goal", self.user)
        self.assertEqual(state.status, "failed")
        self.assertIn("could not parse", state.final_answer)

    def test_unknown_agent_recorded_and_continues(self):
        bad = '{"goal_met": false, "agent": "ghost_agent", "action": "x", "params": {}}'
        provider = FakeProvider([bad] * 5)
        orch = Orchestrator(provider, max_steps=2)
        state = orch.run("goal", self.user)
        self.assertEqual(state.status, "failed")
        self.assertEqual(len(state.steps), 2)
        self.assertFalse(state.steps[0]["result"]["ok"])

    def test_max_steps_reached_without_goal_met(self):
        step = '{"goal_met": false, "agent": "data_agent", "action": "query_application_data", "params": {"query_type": "salary"}}'
        provider = FakeProvider([step] * 10)
        with patch(
            "core.services.ai.orchestration.agents.data_agent.validate_and_execute_tool",
            return_value=({"status": "success"}, {"ok": True, "data": []}),
        ):
            orch = Orchestrator(provider, max_steps=3)
            state = orch.run("goal", self.user)
        self.assertEqual(state.status, "failed")
        self.assertEqual(len(state.steps), 3)
        self.assertIn("did not reach a goal-met", state.final_answer)


class AgentActionAllowlistTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="orch_user2", password="password123")
        self.state = TaskState(goal="g", owner=self.user)

    def test_data_agent_rejects_out_of_scope_action(self):
        result = DataAgent().run("create_scenario", {}, self.state)
        self.assertFalse(result["ok"])

    def test_scenario_agent_rejects_out_of_scope_action(self):
        result = ScenarioAgent().run("query_application_data", {}, self.state)
        self.assertFalse(result["ok"])

    def test_advisor_agent_rejects_unknown_service(self):
        result = AdvisorAgent().run("not_a_real_service", {}, self.state)
        self.assertFalse(result["ok"])

    def test_advisor_agent_lists_real_services(self):
        actions = AdvisorAgent().available_actions()
        self.assertIn("overview", actions)
        self.assertIn("risk_analysis", actions)


class AIChatViewMultiAgentToggleTest(TestCase):
    """Confirms the chat endpoint actually routes to Orchestrator when the
    setting is on, and does NOT when it's off (default)."""

    def setUp(self):
        self.user = User.objects.create_user(username="chat_user", password="password123")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)

    def test_disabled_by_default(self):
        from core.models import AppSettings

        self.assertEqual(AppSettings.get("ai_multi_agent_enabled", "false"), "false")

    def test_enabled_setting_routes_to_orchestrator(self):
        from core.models import AppSettings

        AppSettings.set("ai_multi_agent_enabled", "true")
        fake_provider = FakeProvider(['{"goal_met": true, "final_answer": "orchestrated answer"}'])

        with patch(
            "core.views.ai_chat.ai_chat_core_views.get_active_ai_provider",
            return_value=fake_provider,
        ), patch(
            "core.views.ai_chat.ai_chat_core_views.try_direct_answer",
            return_value=None,
        ):
            response = self.client.post(
                "/api/financial-advisor/ai/chat/",
                data='{"message": "orchestrated test question"}',
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"]["content"], "orchestrated answer")
