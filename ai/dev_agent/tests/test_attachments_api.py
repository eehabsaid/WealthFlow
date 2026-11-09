"""Over HTTP with a real server: attachments reach the model, the picker's per-task override, shared settings, vision flag, cookie session."""

import base64

import pytest

from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.apihelp import TOKEN, Api
from ai.dev_agent.tests.fakes import Scripted, edit, final, plan

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()
PLAN = plan(files_add=["app/more.py"], files_edit=[], steps=[{"title": "go", "files": ["app/more.py"]}])


@pytest.fixture
def make(repo):
    made = []

    def build(*providers):
        made.append(Api(repo, *providers))
        return made[-1]
    yield build
    for a in made:
        a.close()


def test_file_attachment_reaches_the_model_in_every_phase_and_is_listed_without_content(make):
    model = Scripted([PLAN, edit({"path": "app/more.py", "content": "X = 1\n"}), final("done")])
    api = make(model)
    status, body = api.json("POST", "/api/tasks", {"goal": "use the spec", "attachments": [{"kind": "file", "name": "spec.md", "text": "RULE: X must be 1"}]})
    assert status == 202
    api.wait_idle()
    first = model.calls[0][1][0]["content"]
    assert "OWNER-ATTACHED FILES" in first and "RULE: X must be 1" in first
    api.json("POST", f"/api/tasks/{body['id']}/approve")
    api.wait_idle()
    assert "RULE: X must be 1" in model.calls[1][1][0]["content"], "the executing package sees the attachment too"
    task = api.json("GET", f"/api/tasks/{body['id']}")[1]
    assert task["attachments"][0]["name"] == "spec.md" and "RULE" not in str(task)
    events = api.json("GET", f"/api/tasks/{body['id']}/events")[1]["events"]
    assert [e for e in events if e["type"] == "attachments"][0]["items"][0]["omitted"] == 0


def test_oversized_attachment_is_reported_as_an_excerpt_in_the_event_feed(make):
    api = make(Scripted([PLAN]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t", "attachments": [{"kind": "file", "name": "big.log", "text": "z" * 100_000}]})[1]["id"]
    api.wait_idle()
    item = [e for e in api.json("GET", f"/api/tasks/{task_id}/events")[1]["events"] if e["type"] == "attachments"][0]["items"][0]
    assert item["chars"] == 100_000 and item["omitted"] > 50_000


def test_refused_attachments_start_no_task_and_say_why(make):
    api = make(Scripted([PLAN]))
    status, body = api.json("POST", "/api/tasks", {"goal": "t", "attachments": [{"kind": "image", "name": "a.png", "mime": "image/png", "data": PNG}]})
    assert status == 400 and body["code"] == "attachments" and "does not accept images" in body["error"]
    status, body = api.json("POST", "/api/tasks", {"goal": "t", "attachments": [{"kind": "file", "name": ".env", "text": "K=1"}]})
    assert status == 400 and ".env" in body["error"]
    assert api.json("GET", "/api/tasks")[1]["tasks"] == []


def test_image_reaches_a_vision_model(make):
    model = Scripted([PLAN])
    model.vision = True
    api = make(model)
    assert api.json("POST", "/api/tasks", {"goal": "match the picture", "attachments": [{"kind": "image", "name": "a.png", "mime": "image/png", "data": PNG}]})[0] == 202
    api.wait_idle()
    msg = model.calls[0][1][0]
    assert msg["images"] == [{"mime": "image/png", "data": PNG}] and "OWNER-ATTACHED IMAGES: 1" in msg["content"]


def test_model_override_is_for_this_task_only_and_follows_it_to_approval(make, repo):
    api = make(Scripted([PLAN, edit({"path": "app/more.py", "content": "X = 1\n"}), final("ok")]))
    seen = []
    original = api.server.service.provider_factory
    api.server.service.provider_factory = lambda settings: (seen.append((settings["provider"], settings["model"])), original(settings))[1]
    before = Settings(repo).load()
    task_id = api.json("POST", "/api/tasks", {"goal": "t", "provider": "ollama", "model": "special:7b"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    api.wait_idle()
    assert seen[-2:] == [("ollama", "special:7b")] * 2, seen
    assert Settings(repo).load()["model"] == before["model"], "the shared settings are untouched"
    assert api.json("GET", f"/api/tasks/{task_id}")[1]["model_override"] == {"provider": "ollama", "model": "special:7b"}
    assert api.json("POST", "/api/tasks", {"goal": "t", "provider": "nobody"})[0] == 400


def test_picker_choice_is_the_shared_setting_every_interface_reads(make, repo):
    api = make(Scripted([PLAN]))
    assert api.json("PUT", "/api/settings", {"values": {"provider": "anthropic", "model": "claude-sonnet-4"}})[0] == 200
    shared = Settings(repo).load()   # what the CLI reads
    assert (shared["provider"], shared["model"]) == ("anthropic", "claude-sonnet-4")
    state = api.json("GET", "/api/state")[1]
    assert (state["provider"], state["model"], state["vision"]) == ("anthropic", "claude-sonnet-4", True)
    api.json("PUT", "/api/settings", {"values": {"provider": "openai", "model": "gpt-3.5-turbo"}})
    state = api.json("GET", "/api/state")[1]
    assert state["vision"] is False and "not known to accept images" in state["vision_note"]


def test_changed_files_list_has_added_and_removed_counts(make):
    api = make(Scripted([PLAN, edit({"path": "app/more.py", "content": "A = 1\nB = 2\n"}), final("ok")]))
    task_id = api.json("POST", "/api/tasks", {"goal": "t"})[1]["id"]
    api.wait_idle()
    api.json("POST", f"/api/tasks/{task_id}/approve")
    api.wait_idle()
    row = api.json("GET", f"/api/tasks/{task_id}/files")[1]["files"][0]
    assert (row["added"], row["removed"]) == (2, 0)


def test_session_cookie_replaces_the_token_for_the_page_and_only_same_origin(make):
    api = make(Scripted([PLAN]))
    status, _, head = api.call("POST", "/api/session", {})
    cookie = head["Set-Cookie"]
    assert status == 200 and "HttpOnly" in cookie and "SameSite=Strict" in cookie and cookie.startswith(f"devagent_{api.port}=")
    same = {"Cookie": cookie.split(";")[0], "Sec-Fetch-Site": "same-origin"}
    assert api.json("GET", "/api/health", token=None, headers=same)[0] == 200
    assert api.json("GET", "/api/health", token=None, headers={"Cookie": same["Cookie"]})[0] == 401, "no same-origin proof, no cookie login"
    assert api.json("GET", "/api/health", token=None, headers={**same, "Sec-Fetch-Site": "cross-site"})[0] == 403
    assert api.json("GET", "/api/health", token=None, headers={**same, "Origin": "http://evil.example"})[0] == 403
    assert api.json("GET", "/api/health", token=None, headers={"Cookie": f"devagent_{api.port}=wrong", "Sec-Fetch-Site": "same-origin"})[0] == 401
    assert api.json("GET", "/api/health", token="bad", headers=same)[0] == 401, "a wrong bearer is never rescued by a cookie"
    assert TOKEN not in api.call("GET", "/api/state")[1].decode()
