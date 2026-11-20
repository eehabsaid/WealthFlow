"""General tools (write/edit/glob/list/todo/web/subagent), the registry and plugins, AGENTS.md rules, context compaction and the direct (no-plan) mode."""


import sys

from ai.dev_agent.core import rules
from ai.dev_agent.engine import budget
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver
from ai.dev_agent.tests.native_fakes import Native, call as native_call, say
from ai.dev_agent.tools import REGISTRY, Tool, call, plugins, register, web
from ai.dev_agent.tools.registry import schema, unregister


def direct(repo, provider, approver=None, **settings):
    return Agent(repo, provider, {**Settings(repo).load(), "require_plan_approval": False, **settings}, approver or Approver(False))


# ---- files ----
def test_write_file_creates_and_overwrite_needs_a_read_first(ctx, repo):
    assert call(ctx, "write_file", {"path": "app/new.py", "content": "X = 1\n"})["state"] == "written"
    assert call(ctx, "write_file", {"path": "app/calc.py", "content": "Y = 1\n", "overwrite": True})["error"].startswith("read app/calc.py")
    call(ctx, "read_file", {"path": "app/calc.py"})
    assert call(ctx, "write_file", {"path": "app/calc.py", "content": "Y = 1\n", "overwrite": True})["ok"] and (repo.root / "app/calc.py").read_text() == "Y = 1\n"


def test_edit_file_is_exact_and_sha_checked(ctx, repo):
    call(ctx, "read_file", {"path": "app/calc.py"})
    (repo.root / "app/calc.py").write_text("def add(a, b):\n    return a + b  # changed outside\n")
    assert "changed since" in call(ctx, "edit_file", {"path": "app/calc.py", "old": "a + b", "new": "b + a"}).get("error", "changed since")
    call(ctx, "read_file", {"path": "app/calc.py"})
    assert call(ctx, "edit_file", {"path": "app/calc.py", "old": "return a + b", "new": "return b + a"})["state"] == "written"
    assert "error" in call(ctx, "edit_file", {"path": "app/calc.py", "old": "no such text", "new": "x"})


def test_edit_file_keeps_the_protected_file_guard(ctx):
    call(ctx, "read_file", {"path": "app/money.py"})
    out = call(ctx, "edit_file", {"path": "app/money.py", "old": "1", "new": "2"})
    assert "error" in out and ctx.approver.asked and "PROTECTED" in ctx.approver.asked[0][1]


def test_glob_and_list_dir_skip_internal_and_secret_files(ctx):
    assert set(call(ctx, "glob", {"pattern": "**/*.py"})["files"]) >= {"app/calc.py", "tests/test_calc.py", "app/util.py"}
    assert call(ctx, "glob", {"pattern": "*.py", "path": "app"})["files"][0].startswith("app/")
    listing = call(ctx, "list_dir", {})["entries"]
    assert "app/" in listing and ".env" not in listing and not any(e.startswith("coding_agent") for e in listing)
    assert "app/calc.py" in call(ctx, "list_dir", {"path": "app"})["entries"] and "error" in call(ctx, "list_dir", {"path": "nope"})


# ---- todo ----
def test_todo_is_stored_in_the_ledger_and_announced(ctx):
    seen = []
    ctx.emit = seen.append
    out = call(ctx, "todo", {"items": [{"text": "a", "status": "done"}, {"text": "b", "status": "in_progress"}, "c"]})
    assert out["open"] == 2 and ctx.ledger.data["todos"][2] == {"text": "c", "status": "pending"} and seen[0]["type"] == "todo"
    assert "items" in call(ctx, "todo", {"items": []})["error"]


def test_an_open_checklist_is_pointed_out_once_before_the_answer_is_accepted(repo):
    model = Native([native_call(("todo", {"items": [{"text": "step", "status": "in_progress"}]})), say("done"), say("all done now")])
    led = direct(repo, model).start("what is in app?")
    assert led.data["status"] == "answered" and "open items" in model.calls[2]["messages"][-1]["content"]


# ---- web ----
def test_web_fetch_converts_html_and_refuses_private_addresses(ctx, monkeypatch):
    monkeypatch.setattr(web, "_get", lambda url, data=None, timeout=30, hops=5: (url, "text/html; charset=utf-8", b"<html><head><title>T</title><style>x{}</style></head><body><h1>Hi</h1><p>there</p><script>bad()</script></body></html>"))
    out = call(ctx, "web_fetch", {"url": "https://example.org/x"})
    assert out["title"] == "T" and "Hi" in out["text"] and "there" in out["text"] and "bad()" not in out["text"] and "x{}" not in out["text"]
    monkeypatch.undo()
    assert "not a public address" in call(ctx, "web_fetch", {"url": "http://127.0.0.1:8000/x"})["error"]
    assert "http" in call(ctx, "web_fetch", {"url": "file:///etc/passwd"})["error"]


def test_web_search_parses_results(ctx, monkeypatch):
    page = ('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F">Python <b>docs</b></a>'
            '<a class="result__snippet" href="x">The docs &amp; more</a><a class="result__a" href="https://b.example/">B</a>')
    monkeypatch.setattr(web, "_get", lambda url, data=None, timeout=30, hops=5: (url, "text/html", page.encode()))
    out = call(ctx, "web_search", {"query": "python docs", "max_results": 5})
    assert out["results"][0] == {"title": "Python docs", "url": "https://docs.python.org/3/", "snippet": "The docs & more"} and out["results"][1]["url"] == "https://b.example/"


# ---- subagent ----
def test_subagent_runs_a_read_only_conversation_and_returns_its_answer(repo):
    model = Native([native_call(("subagent", {"task": "find add"})), native_call(("grep", {"pattern": "def add"})), say("add is in app/calc.py:1"), say("found it")])
    led = direct(repo, model).start("where is add defined?")
    assert led.data["status"] == "answered" and led.data["answer"] == "found it"
    inner = model.calls[1]
    names = {t["name"] for t in inner["tools"]}
    assert "subagent" not in names and "shell" not in names and "edit_file" not in names and "grep" in names
    assert "app/calc.py:1" in model.calls[3]["messages"][-1]["content"]


# ---- registry and plugins ----
def test_a_tool_can_be_added_without_touching_the_loop(repo):
    register(Tool("ping", lambda c, a: {"pong": a["word"]}, "args {word}: echo it", params=schema({"word": "string"}, ["word"])))
    try:
        model = Native([native_call(("ping", {"word": "hi"})), say("pinged")])
        led = direct(repo, model).start("ping hi")
        assert "ping" in {t["name"] for t in model.calls[0]["tools"]} and '"pong": "hi"' in model.calls[1]["messages"][2]["content"] and led.data["status"] == "answered"
    finally:
        unregister("ping")


def test_plugins_load_from_the_agent_folder_and_a_broken_one_is_reported(repo):
    folder = repo.agent_dir / "tools"
    folder.mkdir()
    (folder / "hello.py").write_text('from ai.dev_agent.tools.registry import tool, schema\n\n@tool("hello_plugin", "args {}: says hello", params=schema())\ndef hello(ctx, args):\n    return {"hi": 1}\n', encoding="utf-8")
    (folder / "broken.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    try:
        problems = plugins.load(repo)
        assert "hello_plugin" in REGISTRY and any("broken.py" in p and "boom" in p for p in problems)
    finally:
        unregister("hello_plugin")


def test_unknown_tools_and_bad_arguments_come_back_as_errors(ctx):
    assert "unknown tool 'nope'" in call(ctx, "nope", {})["error"] and call(ctx, "glob", {})["error"].startswith("missing required")


# ---- rules ----
def test_agents_md_goes_into_the_system_prompt(repo):
    (repo.root / "AGENTS.md").write_text("Always answer in French.\n", encoding="utf-8")
    model = Native([say("oui")])
    direct(repo, model).start("what is in app?")
    assert "Always answer in French." in model.calls[0]["system"] and "Project rules" in model.calls[0]["system"]


def test_rules_files_are_configurable_clipped_and_never_secret(repo):
    (repo.root / "docs").mkdir()
    (repo.root / "docs" / "r.md").write_text("x" * 20000, encoding="utf-8")
    repo.config["rules_files"] = ["docs/r.md", ".env", "missing.md", "../outside.md"]
    text = rules.load(repo)
    assert text.count("###") == 1 and "KEY=secret" not in text and len(text) < rules.PER_FILE + 400 and "omitted" in text


# ---- context compaction ----
def native_turns(count, size=4000):
    out = [{"role": "user", "content": "TASK: x"}]
    for i in range(count):
        out += [{"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}", "name": "read_file", "args": {"path": f"f{i}.py"}}]},
                {"role": "tool", "tool_call_id": f"c{i}", "name": "read_file", "content": "TOOL RESULT read_file:\n" + "x" * size}]
    return out


def test_compaction_clips_old_results_first():
    b, messages = budget.Budget(12000, 2000), native_turns(30)
    assert b.compact("sys", messages) > 0 and len(messages) == 61 and len(messages[2]["content"]) < 700 and len(messages[-1]["content"]) > 3000   # clipped, nothing dropped


def test_compaction_drops_whole_turns_and_lists_them():
    b, messages = budget.Budget(12000, 2000), native_turns(200)
    assert b.compact("sys", messages) > 0 and b.used("sys", messages) <= b.limit
    assert messages[0]["content"].count("earlier steps were dropped") == 1 and "in all" in messages[0]["content"] and "read_file(f159.py)" in messages[0]["content"]
    for i, m in enumerate(messages):   # every tool result still follows the assistant message that made the call
        if m["role"] == "tool":
            assert messages[i - 1]["role"] == "assistant" and messages[i - 1]["tool_calls"][0]["id"] == m["tool_call_id"]
    assert messages[-1]["tool_call_id"] == "c199"   # the newest turn is intact


def test_the_default_window_keeps_28k_free_of_150k():
    b = budget.Budget()
    assert b.window == 150000 and b.limit == 122000


def test_a_big_tool_result_is_truncated_before_it_reaches_the_model(repo):
    (repo.root / "big.txt").write_text("line\n" * 60000, encoding="utf-8")
    model = Native([native_call(("shell", {"command": "type big.txt" if sys.platform == "win32" else "cat big.txt"})), say("read")])
    direct(repo, model).start("what is in big.txt?")
    content = model.calls[1]["messages"][2]["content"]
    assert len(content) < 40000 and "omitted" in content


# ---- direct mode ----
def test_direct_mode_edits_anywhere_but_deleting_still_asks(repo):
    asker = Approver(False)
    model = Native([native_call(("write_file", {"path": "app/brand_new.py", "content": "Z = 1\n"})), native_call(("delete_file", {"path": "app/old.py"})), say("created; delete refused")])
    led = direct(repo, model, asker).start("create app/brand_new.py and remove app/old.py")
    assert led.data["status"] == "completed" and (repo.root / "app/brand_new.py").exists() and (repo.root / "app/old.py").exists()
    assert asker.asked and "delete app/old.py" in asker.asked[0][1] and led.data["plan"]["direct"] is True


def test_direct_mode_still_asks_for_protected_files(repo):
    asker = Approver(False)
    model = Native([native_call(("read_file", {"path": "app/money.py"})), native_call(("edit_file", {"path": "app/money.py", "old": "1", "new": "2"})), say("refused")])
    direct(repo, model, asker).start("change the balance constant in app/money.py")
    assert any("PROTECTED" in m for _, m in asker.asked) and (repo.root / "app/money.py").read_text() == "BALANCE = 1\n"
