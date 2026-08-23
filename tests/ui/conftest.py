"""
Shared pytest fixtures for WealthFlow UI (Playwright) tests.

Provides:
- `base_url`   : root URL of the running WealthFlow instance under test.
- `browser`    : a single Chromium browser instance shared for the whole session.
- `context`    : a fresh browser context (viewport, isolation) per test.
- `page`       : a fresh page per test, bound to `context`.
- automatic Allure screenshot attachment on test failure.

Run against a non-default target with:
    pytest tests/ui --base-url=http://staging.wealthflow.local
"""
import os

import allure
import pytest
from playwright.sync_api import sync_playwright

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_VIEWPORT = {"width": 1280, "height": 800}


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=os.environ.get("WEALTHFLOW_BASE_URL", DEFAULT_BASE_URL),
        help="Base URL of the WealthFlow instance to run UI tests against.",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run the browser with a visible UI instead of headless.",
    )


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance, request):
    headless = not request.config.getoption("--headed")
    browser = playwright_instance.chromium.launch(headless=headless)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    context = browser.new_context(viewport=DEFAULT_VIEWPORT)
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach a screenshot (and page URL) to the Allure report whenever a
    test using the `page` fixture fails."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page is not None:
            try:
                allure.attach(
                    page.screenshot(full_page=True),
                    name="failure-screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
                allure.attach(
                    page.url,
                    name="failure-url",
                    attachment_type=allure.attachment_type.TEXT,
                )
            except Exception:
                # Never let screenshot capture mask the real test failure.
                pass
