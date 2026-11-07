"""Playwright fixtures shared by the browser tests. Skipped when Playwright or a Chromium build is not available."""

import glob
import os

import pytest


def chromium():
    for pattern in (os.environ.get("DEV_AGENT_CHROMIUM", ""), "/opt/pw-browsers/chromium-*/chrome-linux*/chrome"):
        found = sorted(glob.glob(pattern)) if pattern else []
        if found:
            return found[-1]
    return None


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=chromium(), args=["--no-sandbox"]) if chromium() else p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:   # no browser installed
            pytest.skip(f"no Chromium available: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    pg = browser.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    yield pg
    pg.close()
