"""
WealthFlow QA Module — Legal: Privacy Policy, Terms of Service, signup consent
Tests (read-only: no account is ever created):
 1. /privacy/ and /terms/ render every section with the "legal review needed" notice (public, no login).
 2. The pages follow the language: Arabic switches the text and flips the page to RTL.
 3. Signup shows a required consent checkbox linking to both pages; the form is invalid until it is ticked.
 4. Login and signup footers link to Terms/Privacy; the in-app sidebar footer links to them too.

Phases 1-3 run in their own isolated browser WITHOUT a session (the pages are public, and the signup
form is only meaningful logged out). Phase 4 uses the shared admin session.
NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

from tests.core.test_context import TestContext

BASE = "http://127.0.0.1:8000"
PRIVACY_SECTIONS = 8
TERMS_SECTIONS = 9


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "legal", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Legal", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _check_public_pages(page, reporter, screenshot_logger):
    for path, label, count, tab in (
        ("/privacy/", "Privacy Policy", PRIVACY_SECTIONS, "privacy"),
        ("/terms/", "Terms of Service", TERMS_SECTIONS, "terms"),
    ):
        page.goto(f"{BASE}{path}")
        page.wait_for_timeout(1200)
        reporter.pages_visited.add(label)
        sections = page.locator(".legal-section").count()
        draft = page.locator(".legal-draft").is_visible()
        on_page = path in page.url
        _step(reporter, screenshot_logger, page, f"{label} page renders all sections with draft notice",
              on_page and sections == count and draft, f"url={page.url} sections={sections}/{count} draft_notice={draft}", tab)


def _check_arabic_rtl(page, reporter, screenshot_logger):
    page.goto(f"{BASE}/privacy/")
    page.wait_for_timeout(800)
    page.select_option("#authLanguageSelect", "ar")
    page.wait_for_timeout(1500)
    direction = page.evaluate("document.documentElement.dir")
    h1 = page.inner_text("h1")
    ok = direction == "rtl" and h1 != "Privacy Policy"
    _step(reporter, screenshot_logger, page, "Legal page switches to Arabic and RTL", ok, f"dir={direction} h1={h1}", "privacy_ar")
    page.select_option("#authLanguageSelect", "en")
    page.wait_for_timeout(800)


def _check_signup_consent(page, reporter, screenshot_logger):
    page.goto(f"{BASE}/accounts/signup/")
    page.wait_for_timeout(1200)
    box = page.locator("#signupAcceptTerms")
    present = box.count() == 1 and box.get_attribute("required") is not None
    links = page.evaluate(
        "[...document.querySelectorAll('label.signup-terms a')].map(a => a.getAttribute('href'))"
    )
    page.fill("#signupUsernameInput", "legal_probe")
    page.fill("#signupEmailInput", "legal_probe@example.com")
    page.fill("#signupPasswordInput", "SecurePass123!")
    page.fill("#signupConfirmPasswordInput", "SecurePass123!")
    invalid_before = not page.evaluate("document.getElementById('signupForm').checkValidity()")
    box.check()
    valid_after = page.evaluate("document.getElementById('signupForm').checkValidity()")
    ok = present and links == ["/terms/", "/privacy/"] and invalid_before and valid_after
    _step(reporter, screenshot_logger, page, "Signup requires the Terms/Privacy consent checkbox", ok,
          f"present={present} links={links} invalid_before={invalid_before} valid_after={valid_after}", "signup_consent")  # nothing is submitted


def _check_footer_links(context, page, reporter, screenshot_logger):
    for path, tab in (("/accounts/login/", "login_footer"), ("/accounts/signup/", "signup_footer")):
        page.goto(f"{BASE}{path}")
        page.wait_for_timeout(900)
        hrefs = page.evaluate("[...document.querySelectorAll('.auth-legal-links a')].map(a => a.getAttribute('href'))")
        _step(reporter, screenshot_logger, page, f"{path} footer links to Terms and Privacy",
              hrefs == ["/terms/", "/privacy/"], f"hrefs={hrefs}", tab)

    admin = context.page
    context.goto_route("#dashboard")
    admin.wait_for_timeout(1500)
    hrefs = admin.evaluate("[...document.querySelectorAll('.sidebar-legal-links a')].map(a => a.getAttribute('href'))")
    _step(reporter, screenshot_logger, admin, "In-app sidebar footer links to Terms and Privacy",
          hrefs == ["/terms/", "/privacy/"], f"hrefs={hrefs}", "sidebar_footer")


def test_legal_module(context, reporter, screenshot_logger):
    reporter.pages_visited.add("Legal — Privacy / Terms / Signup consent")
    public_ctx = None
    try:
        public_ctx = TestContext(
            context.playwright, headed=context.headed, slow_mo=context.slow_mo,
            device="desktop", theme=context.theme,
        )
        page = public_ctx.page
        _check_public_pages(page, reporter, screenshot_logger)
        _check_arabic_rtl(page, reporter, screenshot_logger)
        _check_signup_consent(page, reporter, screenshot_logger)
        _check_footer_links(context, page, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "legal", "error", "none", "fail", "fail")
        reporter.add_step("Legal module", "Legal", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        if public_ctx:
            try:
                public_ctx.browser.close()
            except Exception:
                pass
