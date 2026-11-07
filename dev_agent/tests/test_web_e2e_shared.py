"""Real-browser tests, part 2: shared settings, cross-interface visibility, and keys/tokens never reaching page scripts."""

import pytest

from .apihelp import TOKEN, Api
from .fakes import Scripted, edit, final, plan
from .test_web_e2e import open_ui

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def test_picker_changes_the_shared_setting_and_disables_images_without_vision(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api)
        page.click("#model-chip")
        page.wait_for_selector(".picker")
        assert api.json("GET", "/api/state")[1]["vision"] is False
        expect(page.locator("#attach-image")).to_be_disabled()
        api.json("PUT", "/api/settings", {"values": {"provider": "anthropic", "model": "claude-sonnet-4"}})
        page.reload()
        page.wait_for_selector("#goal")
        assert "claude-sonnet-4" in page.inner_text("#model-chip")
        expect(page.locator("#attach-image")).to_be_enabled()
    finally:
        api.close()


def test_stage4_cross_interface_visibility_and_no_secrets_in_page(page, repo):
    """A plan created over the API (as the CLI/VS Code would) is visible in the browser and can be approved there; no token/key ever reaches page scripts."""
    secret = "sk-SECRETSECRETSECRET1234"
    api = Api(repo, Scripted([plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "go", "files": ["app/more.py"]}]),
                              edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")]))
    try:
        api.store.data["openai"] = secret
        requests = []
        page.on("request", lambda r: requests.append((r.url, dict(r.headers), r.post_data or "")))
        task_id = api.json("POST", "/api/tasks", {"goal": "from another interface"})[1]["id"]
        api.wait_idle()
        open_ui(page, api)
        page.click("#history-btn")
        page.click(".task-row")
        page.click("[data-act=approve]")
        page.wait_for_selector(".final")
        assert api.json("GET", f"/api/tasks/{task_id}")[1]["status"] == "completed", "approved in the browser, visible to every interface"
        assert page.evaluate("document.cookie") == "", "the session cookie is HttpOnly: page scripts cannot read it"
        assert TOKEN not in page.content() and secret not in page.content()
        later = [r for r in requests if "/api/session" not in r[0]]
        assert later and not any(TOKEN in str(r[1]) or TOKEN in r[0] or TOKEN in r[2] or secret in str(r) for r in later), "no token or key in any later request"
        assert api.json("GET", "/api/keys")[1]["keys"]["openai"] is True and secret not in api.call("GET", "/api/keys")[1].decode()
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
        assert api.json("GET", "/api/settings")[1]["model"] == "gpt-test"
    finally:
        api.close()
