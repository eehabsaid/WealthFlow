"""
Unit test suite for AI Financial Advisor Phase 3: AI Actions.

Tests tool registration, the 5-step validation pipeline, tool handlers,
atomic scenario creation rollback, read-only constraints, audit logging,
and single-tool call chat controller integration.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Scenario, ScenarioEvent
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)

User = get_user_model()

class AIToolsValidationTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = User.objects.create_user(username="action_user", password="password123")
        self.inactive_user = User.objects.create_user(
            username="inactive_user", password="password123", is_active=False
        )

    def test_registered_tools_schema_structure(self):
        schemas = get_registered_tool_schemas()
        self.assertEqual(len(schemas), 9)
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("create_scenario", names)
        self.assertIn("compare_scenarios", names)
        self.assertIn("summarize_report", names)
        self.assertIn("explain_chart", names)
        self.assertIn("suggest_optimizations", names)
        self.assertIn("read_live_app_structure", names)
        self.assertIn("suggest_app_feature", names)
        self.assertIn("query_application_data", names)
        self.assertIn("read_application_codebase", names)

    def test_validation_pipeline_step_1_unknown_tool_rejection(self):
        # Step 1: Unknown tool name MUST return status="rejected" audit record and error (User rule & Rule 3)
        audit, res = validate_and_execute_tool("unknown_fake_tool", {}, self.user)
        self.assertFalse(res["ok"])
        self.assertIn("Unknown tool", res["error"])
        self.assertEqual(audit["status"], "rejected")
        self.assertEqual(audit["tool"], "unknown_fake_tool")
        self.assertIn("Unknown tool", audit["rejection_reason"])
        self.assertEqual(audit["duration_ms"], 0)

    def test_validation_pipeline_step_2_invalid_parameters(self):
        # Step 2: Missing required parameter 'name' for create_scenario
        audit, res = validate_and_execute_tool("create_scenario", {}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("Missing required parameter", audit["rejection_reason"])

        # Wrong type for compare_scenarios
        audit, res = validate_and_execute_tool("compare_scenarios", {"scenario_ids": "not_a_list"}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")

        # Unknown service_key for summarize_report
        audit, res = validate_and_execute_tool("summarize_report", {"service_key": "invalid_key_123"}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")

    def test_validation_pipeline_step_3_unauthenticated_user(self):
        # Step 3: Anonymous / None user MUST be rejected
        audit, res = validate_and_execute_tool("summarize_report", {"service_key": "overview"}, None)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("authentication required", audit["rejection_reason"].lower())

    def test_validation_pipeline_step_4_unauthorized_user(self):
        # Step 4: Inactive user MUST be rejected
        audit, res = validate_and_execute_tool("summarize_report", {"service_key": "overview"}, self.inactive_user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("inactive", audit["rejection_reason"].lower())

    def test_validation_pipeline_step_5_business_rules_and_atomic_rollback(self):
        # Step 5: Invalid event inside create_scenario MUST be rejected before mutation
        initial_sc_count = Scenario.objects.count()
        initial_ev_count = ScenarioEvent.objects.count()

        invalid_events = [
            {"event_type": "house", "event_date": "2026-06-01"},
            {"event_type": "", "event_date": ""},  # Invalid!
        ]
        audit, res = validate_and_execute_tool(
            "create_scenario",
            {"name": "Bad Scenario", "events": invalid_events},
            self.user,
        )
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")

        # Confirm atomic rollback — zero scenarios or events created
        self.assertEqual(Scenario.objects.count(), initial_sc_count)
        self.assertEqual(ScenarioEvent.objects.count(), initial_ev_count)
