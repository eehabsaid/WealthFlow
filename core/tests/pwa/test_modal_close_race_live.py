"""Real-browser regression test for the shared #globalModal: a Close issued while Bootstrap's show-transition is
still running used to be ignored (hide() is a no-op mid-transition), leaving the modal stuck open."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from core.tests.billing.test_support import grant_ai_workspace_access


class GlobalModalCloseRaceLiveTests(StaticLiveServerTestCase):
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
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(username="modal_user", password="pw123456")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.page = ctx.new_page()
        self.addCleanup(ctx.close)
        self.page.goto(f"{self.live_server_url}/#dashboard")
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
            skip.click()
            self.page.wait_for_selector("#globalModal.show", state="detached", timeout=20000)
        except Exception:
            pass
        self.page.wait_for_timeout(1500)                     # let the onboarding modal's hide animation finish
        self.page.wait_for_function("() => typeof showModal === 'function' && typeof closeModal === 'function'", timeout=20000)

    def modal_open(self):
        return self.page.evaluate("""() => {
            const el = document.getElementById('globalModal');
            const inst = el && bootstrap.Modal.getInstance(el);
            return !!(el && (el.classList.contains('show') || (inst && inst._isShown)));
        }""")

    def test_close_during_show_transition_still_closes(self):
        for _ in range(5):                                   # same tick: show() then close(), the worst case
            self.page.evaluate("() => { showModal('<div class=\"modal-body\">x</div>'); closeModal(); }")
            self.page.wait_for_timeout(1500)                 # let every Bootstrap transition settle
            self.assertFalse(self.modal_open(), "Close issued mid show-transition was ignored: modal stuck open")

    def test_close_after_fully_shown_and_reopen_still_work(self):
        self.page.evaluate("() => showModal('<div class=\"modal-body\">one</div>')")
        self.page.wait_for_selector("#globalModal.show .modal-body:has-text('one')", timeout=10000)
        self.page.wait_for_timeout(800)                      # show transition finished
        self.page.evaluate("() => closeModal()")
        self.page.wait_for_timeout(1200)                     # hide transition finished
        self.assertFalse(self.modal_open())
        self.page.evaluate("() => showModal('<div class=\"modal-body\">two</div>')")   # reopen must not be swallowed
        self.page.wait_for_selector("#globalModal.show .modal-body:has-text('two')", timeout=10000)
        self.page.wait_for_timeout(1200)                     # a leftover close handler would hide it by now
        self.assertTrue(self.modal_open())
