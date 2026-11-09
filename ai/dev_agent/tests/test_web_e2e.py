"""Real-browser tests of the Web UI against a real server with a fake model. Skipped when Playwright or a Chromium build is not available."""

import pytest

from ai.dev_agent.tests.apihelp import TOKEN, Api
from ai.dev_agent.tests.fakes import Blocking, Scripted, edit, final, plan, tool


sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def open_ui(page, api, token=TOKEN):
    page.goto(f"http://127.0.0.1:{api.port}/#token={token}")
    page.wait_for_selector("#goal")


def send(page, text):
    page.fill("#goal", text)
    page.click("#send-btn")


def test_plan_approve_run_and_diff_in_the_browser(page, repo):
    evil = "<img src=x onerror=\"window.__xss=1\">"
    api = Api(repo, Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": evil, "files": ["app/more.py"]}]),
                              edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    try:
        open_ui(page, api)
        assert "token" not in page.url, "the token must be removed from the address bar"
        expect(page.locator("#stop-btn")).to_be_disabled()
        send(page, evil)
        page.wait_for_selector("[data-act=approve]")
        assert evil in page.inner_text(".thread"), "markup must be shown as plain text"
        assert page.evaluate("window.__xss") is None and page.locator(".thread img").count() == 0
        page.click("[data-act=approve]")
        page.wait_for_selector(".final")
        page.click("[data-act=diff]")
        page.wait_for_selector(".diff-body .add")
        assert "X = 1" in page.inner_text(".diff-body")
        expect(page.locator("#stop-btn")).to_be_disabled()
        assert not page.errors, page.errors
    finally:
        api.close()


def test_plan_rejection_changes_nothing(page, repo):
    api = Api(repo, Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "go", "files": ["app/more.py"]}])]))
    try:
        open_ui(page, api)
        send(page, "add more")
        page.click("[data-act=reject]", timeout=20000)
        page.wait_for_selector("[data-act=approve]", state="detached")
        assert not (repo.root / "app/more.py").exists()
        task = api.json("GET", "/api/tasks")[1]["tasks"][0]
        assert task["status"] == "rejected"
    finally:
        api.close()


def test_wrong_token_shows_a_clear_message(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api, token="nope" * 10)
        page.wait_for_selector("#banner:not([hidden])")
        assert "token" in page.inner_text("#banner").lower() or "access" in page.inner_text("#banner").lower()
    finally:
        api.close()


def test_protected_file_approval_card_and_stop(page, repo):
    (repo.root / "app/money.py").write_text("BALANCE = 1\n")
    api = Api(repo, Scripted([plan(files_edit=["app/money.py"], steps=[{"title": "x", "files": ["app/money.py"]}]), tool("read_file", path="app/money.py"),
                              edit({"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]}), final("ok")]))
    try:
        open_ui(page, api)
        send(page, "change balance")
        page.click("[data-act=approve]")
        page.wait_for_selector("[data-act=deny]")
        assert "PROTECTED" in page.inner_text(".thread")
        page.click("[data-act=deny]")
        page.wait_for_selector("[data-act=deny]", state="detached")
        page.wait_for_selector(".final, .error")
        assert (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"
    finally:
        api.close()
    model = Blocking([plan()])
    api = Api(repo, model)
    try:
        open_ui(page, api)
        send(page, "slow")
        page.click("[data-act=approve]")
        assert model.started.wait(10)
        expect(page.locator("#stop-btn")).to_be_enabled()
        page.click("#stop-btn")
        expect(page.locator("#stop-btn")).to_be_disabled()
        page.wait_for_selector("text=stopped", timeout=20000)
    finally:
        api.close()


def test_history_lists_tasks_and_reopens_them(page, repo):
    api = Api(repo, Scripted([plan(), plan()]))
    try:
        open_ui(page, api)
        send(page, "first task here")
        page.wait_for_selector("[data-act=approve]")
        page.click("#new-chat")
        page.click("#history-btn")
        page.wait_for_selector(".task-row")
        assert "first task here" in page.inner_text(".task-row")
        page.click(".task-row")
        page.wait_for_selector("[data-act=approve]")
    finally:
        api.close()
