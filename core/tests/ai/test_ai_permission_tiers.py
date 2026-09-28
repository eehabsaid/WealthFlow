"""Regression/coverage for backlog item 7: explicit Read/Execute/Modify
permission tiers, layered on top of (and kept backward-compatible with) the
older ai_read_only boolean. See core/services/ai/tools/permissions.py for
the tier semantics.
"""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from core.services.ai.tools import validate_and_execute_tool
from core.services.ai.tools.permissions import (
    TIER_EXECUTE,
    TIER_MODIFY,
    TIER_READ,
    normalize_tier,
    resolve_granted_tier,
    tier_index,
    tool_allowed_at_tier,
)
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()


class PermissionTierUnitTest(TestCase):
    def test_tier_ordering(self):
        self.assertLess(tier_index(TIER_READ), tier_index(TIER_EXECUTE))
        self.assertLess(tier_index(TIER_EXECUTE), tier_index(TIER_MODIFY))

    def test_unknown_tier_normalizes_to_read(self):
        self.assertEqual(normalize_tier("nonsense"), TIER_READ)
        self.assertEqual(normalize_tier(None), TIER_READ)
        self.assertEqual(normalize_tier(""), TIER_READ)

    def test_tool_allowed_at_tier(self):
        self.assertTrue(tool_allowed_at_tier(TIER_READ, TIER_READ))
        self.assertTrue(tool_allowed_at_tier(TIER_READ, TIER_MODIFY))
        self.assertFalse(tool_allowed_at_tier(TIER_MODIFY, TIER_READ))
        self.assertFalse(tool_allowed_at_tier(TIER_MODIFY, TIER_EXECUTE))
        self.assertTrue(tool_allowed_at_tier(TIER_MODIFY, TIER_MODIFY))

    def test_resolve_granted_tier_falls_back_to_legacy_read_only(self):
        AppSettings.set("ai_read_only", "true")
        self.assertEqual(resolve_granted_tier(), TIER_READ)
        AppSettings.set("ai_read_only", "false")
        self.assertEqual(resolve_granted_tier(), TIER_MODIFY)

    def test_explicit_tier_setting_takes_priority_over_legacy_boolean(self):
        # Even if the old boolean says "allow everything", an explicit
        # "execute" tier setting must still cap it at execute.
        AppSettings.set("ai_read_only", "false")
        AppSettings.set("ai_permission_tier", "execute")
        self.assertEqual(resolve_granted_tier(), TIER_EXECUTE)


class PermissionTierExecutionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tier_ai_user", password="Password123!")

    def test_execute_tier_still_blocks_modify_tools(self):
        AppSettings.set("ai_permission_tier", "execute")
        audit, res = validate_and_execute_tool("create_scenario", {"name": "Should be blocked"}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("modify", audit["rejection_reason"])

    def test_modify_tier_allows_create_scenario(self):
        AppSettings.set("ai_permission_tier", "modify")
        audit, res = validate_and_execute_tool("create_scenario", {"name": "Allowed via tier"}, self.user)
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")

    def test_read_tier_still_allows_read_tools(self):
        AppSettings.set("ai_permission_tier", "read")
        audit, res = validate_and_execute_tool("query_application_data", {}, self.user)
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")

    def test_invalid_tier_setting_defaults_safely_to_read(self):
        AppSettings.set("ai_permission_tier", "garbage")
        audit, res = validate_and_execute_tool("create_scenario", {"name": "x"}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")


class PermissionTierSettingsEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tier_admin_user", password="Password123!")
        grant_ai_workspace_access(self.user)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        profile = AuthWorkflowService.get_profile(self.user)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.client.force_login(self.user)

    def test_get_returns_permission_tier(self):
        res = self.client.get("/api/settings/ai/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ai_permission_tier", res.json())

    def test_post_saves_permission_tier_and_keeps_legacy_boolean_in_sync(self):
        res = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_permission_tier": "execute", "ai_provider": "ollama"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AppSettings.get("ai_permission_tier", user=self.user), "execute")
        # execute != read, so the legacy read-only boolean must reflect "not read-only".
        self.assertEqual(AppSettings.get("ai_read_only", user=self.user), "false")

    def test_post_rejects_invalid_permission_tier(self):
        res = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_permission_tier": "delete_everything", "ai_provider": "ollama"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_legacy_ai_read_only_post_still_works_unchanged(self):
        """No ai_permission_tier in the payload at all — must behave exactly
        as before this feature existed."""
        res = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_read_only": False, "ai_provider": "ollama"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AppSettings.get("ai_read_only", user=self.user), "false")
        self.assertEqual(AppSettings.get("ai_permission_tier", user=self.user), "modify")
