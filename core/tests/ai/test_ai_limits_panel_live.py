"""Real-browser test (Chromium via Playwright) of the sysadmin "Monthly AI token limit per user" frame and the
"Installed Models" table on Settings > AI Advisor: layout order, shared Show all / Show less toggle, search,
Toggle Select All and bulk apply. Skipped when Chromium is not installed."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from core.authentication.services import AuthWorkflowService
from core.constants.ai_user_settings import USER_LIMIT_KEY, USE_GENERAL_KEY
from core.models import AIModelVersion, AppSettings, Subscription
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()


class AILimitsPanelLiveTests(StaticLiveServerTestCase):
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
        self.admin = User.objects.create_user(username="limits_admin", password="pw123456", is_staff=True)
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(self.admin)   # /api/ai-platform/* is subscription-gated
        self.users = [User.objects.create_user(username=f"lim_user_{i}", password="pw123456", email=f"u{i}@x.io") for i in range(7)]
        AppSettings.set(USE_GENERAL_KEY, "false", user=self.users[6])      # one user on own settings
        for i in range(7):
            AIModelVersion.objects.create(version_name=f"model-v{i}", benchmark_score=50 + i)
        self.client.force_login(self.admin)
        ctx = self._browser.new_context(viewport={"width": 1400, "height": 1000})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.page = ctx.new_page()
        self.addCleanup(ctx.close)
        self.page.goto(f"{self.live_server_url}/#settings-aiadvisor")
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
            skip.click()
            self.page.wait_for_selector("#globalModal.show", state="detached", timeout=8000)
        except Exception:
            pass
        if "settings-aiadvisor" not in self.page.url:
            self.page.goto(f"{self.live_server_url}/#settings-aiadvisor")
        self.page.wait_for_selector("#aiLimitsBody tr", timeout=30000)
        self.page.wait_for_selector("#aiPlatformModelList tr td.fw-bold", timeout=30000)

    def rows(self):
        return self.page.locator("#aiLimitsBody tr:visible").count()

    def test_layout_title_input_buttons_and_order(self):
        p = self.page
        # (5) limits frame sits above the Self-Evolving platform card that holds "Installed Models"
        self.assertTrue(p.evaluate("""() => document.getElementById('aiUserLimitsCard')
            .compareDocumentPosition(document.getElementById('aiPlatformModelList')) & Node.DOCUMENT_POSITION_FOLLOWING"""))
        # (1) title is a plain label, not a framed addon; (2) the input is roomy
        self.assertEqual(p.locator("#aiUserLimitsCard .input-group-text").count(), 0)
        self.assertEqual(p.locator("label[for=aiDefaultLimitInput]").inner_text().strip(), "Default limit (tokens / month)")
        self.assertGreaterEqual(p.locator("#aiDefaultLimitInput").bounding_box()["width"], 200)
        # (3) Save buttons use exactly the same classes as the Save beside "Test Connection"
        ref = p.evaluate("() => [...document.getElementById('aiSaveBtn').classList].sort()")
        self.assertEqual(p.evaluate("() => [...document.getElementById('aiDefaultLimitSave').classList].sort()"), ref)
        self.assertEqual(p.evaluate("() => [...document.querySelector('.ai-limit-save').classList].filter(c => c !== 'ai-limit-save').sort()"), ref)

    def test_both_tables_collapse_with_the_shared_toggle(self):
        p = self.page
        # (7) limits table: 8 users (7 + admin) -> 5 visible + "Show all 8 rows"
        self.assertEqual(self.rows(), 5)
        toggle = p.locator("#aiLimitsTableHost .wf-table-toggle-btn")
        self.assertIn("Show all 8", toggle.inner_text())
        toggle.click()
        self.assertEqual(self.rows(), 8)
        self.assertIn("Show less", toggle.inner_text())
        toggle.click()
        self.assertEqual(self.rows(), 5)
        # (6) installed models: more than 5 versions -> 5 visible + toggle; same helper, same labels
        models = lambda: p.locator("#aiPlatformModelList tr:visible").count()
        self.assertEqual(models(), 5)
        mtoggle = p.locator("#aiPlatformModelList").locator("xpath=ancestor::div[contains(@class,'table-container')]/following-sibling::div[contains(@class,'wf-table-toggle-btn')]")
        total = AIModelVersion.objects.count()                      # 7 created here + the seeded baseline
        self.assertGreater(total, 5)
        self.assertIn(f"Show all {total}", mtoggle.inner_text())
        mtoggle.click()
        self.assertEqual(models(), total)
        self.assertIn("Show less", mtoggle.inner_text())
        mtoggle.click()
        self.assertEqual(models(), 5)
        # reloading the list (what Promote / Scan do) must re-arm one fresh toggle, not stack or orphan it
        with p.expect_response(lambda r: "/api/ai-platform/models/" in r.url):
            p.evaluate("() => window.AIA.loadAIPlatformOverviewData()")
        p.wait_for_function("() => document.querySelectorAll('#aiPlatformModelList tr').length > 5")
        self.assertEqual(models(), 5)
        self.assertEqual(mtoggle.count(), 1)                          # exactly one toggle after the reload
        self.assertIn(f"Show all {total}", mtoggle.inner_text())
        mtoggle.click()
        self.assertEqual(models(), total)

    def test_search_toggle_select_all_and_bulk_apply(self):
        p = self.page
        # (4) search narrows the list; clearing restores it
        p.fill("#aiLimitsSearch", "lim_user_3")
        self.assertEqual(self.rows(), 1)
        p.fill("#aiLimitsSearch", "u5@x.io")                      # email search
        self.assertEqual(self.rows(), 1)
        p.fill("#aiLimitsSearch", "no-such-person")
        self.assertIn("No users match", p.locator("#aiLimitsBody").inner_text())
        p.fill("#aiLimitsSearch", "")
        p.select_option("#aiLimitsModeFilter", "own")
        self.assertEqual(self.rows(), 1)
        p.select_option("#aiLimitsModeFilter", "all")
        self.assertEqual(self.rows(), 5)
        # users on their own settings can't be selected
        self.assertEqual(p.locator("#aiLimitsBody .ai-limit-select:disabled").count(), 1)
        self.assertFalse(p.locator("#aiLimitsBulkApply").is_enabled())
        # Toggle Select All selects every eligible user, including rows hidden behind "Show all"
        p.click("#aiLimitsToggleAll")
        self.assertIn("7 selected", p.locator("#aiLimitsSelectedCount").inner_text())
        self.assertTrue(p.locator("#aiLimitsBulkApply").is_enabled())
        self.assertEqual(self.rows(), 5)                              # selection did not collapse/expand the table
        p.click("#aiLimitsToggleAll")
        self.assertIn("0 selected", p.locator("#aiLimitsSelectedCount").inner_text())
        # bulk apply to all eligible users
        p.click("#aiLimitsToggleAll")
        p.fill("#aiLimitsBulkValue", "4242")
        with p.expect_response(lambda r: "user-limits" in r.url and r.request.method == "POST"):
            p.click("#aiLimitsBulkApply")
        p.wait_for_function("() => document.getElementById('aiLimitsSelectedCount').textContent.startsWith('0')")
        for u in self.users[:6] + [self.admin]:
            self.assertEqual(AppSettings.objects.get(key=USER_LIMIT_KEY, owner=u).value, "4242", u.username)
        self.assertFalse(AppSettings.objects.filter(key=USER_LIMIT_KEY, owner=self.users[6]).exists())   # own-settings user untouched
        # single selection + blank value clears the override again
        p.fill("#aiLimitsSearch", "lim_user_2")
        p.click("#aiLimitsToggleAll")
        p.click("#aiLimitsBulkApply")
        p.wait_for_function("() => document.getElementById('aiLimitsSelectedCount').textContent.startsWith('0')")
        self.assertFalse(AppSettings.objects.filter(key=USER_LIMIT_KEY, owner=self.users[2]).exists())

    def test_platform_section_explains_a_missing_subscription(self):
        p = self.page
        Subscription.objects.filter(owner=self.admin).delete()      # lapsed trial / plan without the AI platform
        with p.expect_response(lambda r: "/api/ai-platform/models/" in r.url) as info:
            p.evaluate("() => window.AIA.loadAIPlatformOverviewData()")
        self.assertEqual(info.value.status, 402)
        p.wait_for_function("() => document.getElementById('aiPlatformModelList').textContent.includes('active subscription')")
        self.assertIn("active subscription", p.inner_text("#aiPlatformDatasetHealth"))
        self.assertNotIn("Loading", p.inner_text("#aiPlatformModelList"))
        self.assertEqual(p.locator("#aiPlatformModelList").locator("xpath=ancestor::div[contains(@class,'table-container')]/following-sibling::div[contains(@class,'wf-table-toggle-btn')]").count(), 0)
