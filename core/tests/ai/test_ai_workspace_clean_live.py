"""Real-browser test (Chromium via Playwright) that the AI Workspace is only for end users.

Kept: chat, New Chat, conversation list, Pinned Chats, Saved Prompts, Knowledge Search (+ Learned Answers card).
Removed: right panel (Context Sources, Tools executed, Confidence, App modules), welcome cards (provider, model,
knowledge entries, capabilities, Autonomous Scan) and every "Run Autonomous Scan" button. A member may search
knowledge but not edit it; a system administrator can manage it. Skipped when Chromium is not installed."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache

from core.authentication.services import AuthWorkflowService
from core.models import AIKnowledgeEntry, PagePermission
from core.tests.ai.live_boot import first_load, scale_timeouts
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
GONE_TEXT = ["Context Sources", "Tools Executed", "Confidence", "Application Modules", "Connected Provider", "Active Model",
             "Knowledge Entries", "AI Capabilities", "Autonomous Scan", "Run Autonomous", "Toggle Context Panel"]
GONE_SELECTORS = [".ai-ws-right", "#ai-ws-chip-provider", "#ai-ws-chip-model", "#ai-ws-chip-knowledge", ".ai-ws-platform-card",
                  ".ai-ws-platform-grid", "#ai-ws-toggle-context", "#aiPlatformScanCard"]
KEPT_SELECTORS = ["#ai-ws-input", ".ai-ws-new-chat-btn", "#ai-ws-card-pinned-chats", "#ai-ws-card-saved-prompts",
                  "#ai-ws-card-knowledge-search", "#ai-ws-chip-status"]


class AIWorkspaceCleanLiveTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        super().setUpClass()
        try:
            from playwright.sync_api import sync_playwright

            cls._pw = sync_playwright().start()
            cls._browser = cls._pw.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as exc:
            super().tearDownClass()
            from unittest import SkipTest
            raise SkipTest(f"Chromium not available: {str(exc).splitlines()[0]}")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        AIKnowledgeEntry.objects.create(key="rule_clean", title="Clean rule", content="Body of the rule", category="business_rule")

    def open_as(self, username, sysadmin):
        user = User.objects.create_user(username=username, password="pw123456", is_staff=sysadmin)
        if sysadmin:
            profile = AuthWorkflowService.get_profile(user)
            profile.is_sysadmin = True
            profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(user)
        PagePermission.objects.create(user=user, page="wealthflow_ai", granted=True)
        self.client.force_login(user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        scale_timeouts(ctx)
        self.addCleanup(ctx.close)
        self.page = ctx.new_page()
        first_load(self.page, f"{self.live_server_url}/#ai")
        self.page.wait_for_selector("#ai-ws-input", timeout=15000)

    def assert_clean_workspace(self):
        p = self.page
        p.wait_for_selector(".ai-ws-empty-state", timeout=10000)
        body = p.inner_text("#ai-ws-container, .ai-ws-container, body")
        for text in GONE_TEXT:
            self.assertNotIn(text.lower(), body.lower(), f"'{text}' must not appear in the AI workspace")
        for sel in GONE_SELECTORS:
            self.assertEqual(p.locator(sel).count(), 0, f"{sel} must be gone")
        for sel in KEPT_SELECTORS:
            self.assertGreaterEqual(p.locator(sel).count(), 1, f"{sel} must stay")
        self.assertEqual(p.locator(".ai-ws-suggestion-chip").count(), 4)

    def open_knowledge_search(self):
        self.page.click("#ai-ws-card-knowledge-search")
        self.page.wait_for_selector("#ks-search-input", timeout=8000)
        self.page.wait_for_selector("#ks-modal-body :text('Clean rule')", timeout=8000)

    def test_member_sees_a_clean_workspace_and_can_only_search_knowledge(self):
        self.open_as("clean_member", sysadmin=False)
        self.assert_clean_workspace()
        self.open_knowledge_search()
        self.page.click("#ks-modal-body :text('Clean rule')")
        self.page.wait_for_selector("#ks-modal-body :text('Body of the rule')", timeout=5000)
        self.assertEqual(self.page.locator("#globalModal button:has(.bi-pencil)").count(), 0)
        self.assertEqual(self.page.locator("#globalModal button:has(.bi-trash)").count(), 0)
        self.assertEqual(self.page.locator("#globalModal button:has(.bi-journal-text)").count(), 0)
        self.assertGreaterEqual(self.page.locator("#globalModal button:has(.bi-clipboard)").count(), 1)
        self.assertNotIn("scan", self.page.inner_text("#globalModal").lower())

    def test_sysadmin_manages_knowledge_from_search_and_no_scan_button_exists(self):
        self.open_as("clean_admin", sysadmin=True)
        self.assert_clean_workspace()
        self.open_knowledge_search()
        self.page.click("#ks-modal-body :text('Clean rule')")
        self.page.wait_for_selector("#globalModal button:has(.bi-pencil)", timeout=5000)
        self.assertGreaterEqual(self.page.locator("#globalModal button:has(.bi-trash)").count(), 1)
        self.page.click("#globalModal button:has(.bi-journal-text)")
        self.page.wait_for_selector("#globalModal :text('Knowledge Base')", timeout=8000)
        self.page.wait_for_selector("#globalModal :text('Clean rule')", timeout=8000)
        text = self.page.inner_text("#globalModal").lower()
        self.assertNotIn("scan", text)
        self.assertNotIn("autonomous", text)
        self.assertIn("new entry", text)
