"""Real-browser tests of the Web UI against a real server with a fake model. Skipped when Playwright or a Chromium build is not available."""

import glob
import os

import pytest

from .apihelp import TOKEN, Api
from .fakes import Blocking, Scripted, edit, final, plan, tool

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def chromium():
    for pattern in (os.environ.get("DEV_AGENT_CHROMIUM", ""), "/opt/pw-browsers/chromium-*/chrome-linux*/chrome"):
        found = sorted(glob.glob(pattern)) if pattern else []
        if found:
            return found[-1]
    return None


@pytest.fixture(scope="module")
def browser():
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


def open_ui(page, api, token=TOKEN):
    page.goto(f"http://127.0.0.1:{api.port}/#token={token}")


def test_plan_approve_run_and_diff_in_the_browser(page, repo):
    evil = "<img src=x onerror=\"window.__xss=1\">"
    api = Api(repo, Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": evil, "files": ["app/more.py"]}]),
                              edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    try:
        open_ui(page, api)
        assert "token" not in page.url, "the token must be removed from the address bar"
        page.fill("#goal", evil)
        page.click("#start-btn")
        page.wait_for_selector("text=Approve and run")
        assert evil in page.inner_text("#detail"), "markup must be shown as plain text"
        assert page.evaluate("window.__xss") is None and page.locator("#detail img").count() == 0
        page.click("text=Approve and run")
        page.wait_for_selector(".s-completed")
        page.wait_for_selector(".diff-body .add")
        assert "+X = 1" in page.inner_text(".diff-body")
        assert "Finished: completed" in page.inner_text(".timeline")
        expect(page.locator("#run-state")).to_have_text("idle")   # no string eval: the page CSP forbids it
        assert not page.errors, page.errors
    finally:
        api.close()


def test_wrong_or_missing_token_shows_a_clear_message(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api, token="nope" * 10)
        page.wait_for_selector("#banner:not([hidden])")
        assert "token" in page.inner_text("#banner").lower()
        page.evaluate("sessionStorage.clear()")
        page.goto(f"http://127.0.0.1:{api.port}/")
        assert "No access token" in page.inner_text("#banner")
    finally:
        api.close()


def test_approval_card_and_stop_button(page, repo):
    (repo.root / "app/money.py").write_text("BALANCE = 1\n")
    api = Api(repo, Scripted([plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]), tool("read_file", path="app/money.py"),
                              edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("ok")]))
    try:
        open_ui(page, api)
        page.fill("#goal", "change balance")
        page.click("#start-btn")
        page.click("text=Approve and run")
        page.wait_for_selector(".approval")
        assert "PROTECTED" in page.inner_text(".approval")
        page.click(".approval >> text=Deny")
        page.wait_for_selector(".approval", state="detached")
        page.wait_for_selector(".s-completed, .s-stopped")
        assert (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"
    finally:
        api.close()
    model = Blocking([plan()])
    api = Api(repo, model)
    try:
        open_ui(page, api)
        page.fill("#goal", "slow")
        page.click("#start-btn")
        page.click("text=Approve and run")
        assert model.started.wait(10)
        expect(page.locator("#stop-btn")).to_be_enabled()
        page.click("#stop-btn")
        page.wait_for_selector(".s-stopped")
        assert "stopped by user" in page.inner_text("#detail")
    finally:
        api.close()


def test_settings_dialog_saves_key_without_ever_showing_it(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api)
        page.click("#settings-btn")
        page.select_option("#s-provider", "openai")
        page.fill("#s-model", "gpt-test")
        page.fill("#s-key", "sk-SECRETSECRETSECRET1234")
        page.click("text=Save")
        page.wait_for_selector("text=Saved.")
        assert api.store.data["openai"] == "sk-SECRETSECRETSECRET1234"
        assert page.input_value("#s-key") == "" and "SECRETSECRET" not in page.content()
        assert "stored" in page.inner_text(".settings")
        assert api.json("GET", "/api/settings")[1]["model"] == "gpt-test"
    finally:
        api.close()
