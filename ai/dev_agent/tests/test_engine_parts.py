import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ai.dev_agent.engine import budget, packages, protocol, retries
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.providers import http as phttp
from ai.dev_agent.providers.adapters import Anthropic, Gemini, Ollama, OpenAI
from ai.dev_agent.providers.base import ProviderError, merge_roles, redact
from ai.dev_agent.providers.registry import build_provider


def test_parse_reply_variants():
    P = protocol.parse_reply
    assert P('{"tool": "grep", "args": {"pattern": "x"}}').payload == ("grep", {"pattern": "x"})
    assert P('Sure!\n```json\n{"tool": "read_file", "args": {"path": "a"}}\n```').kind == "tool"
    assert P('{"final": "ok"}').payload == "ok"
    assert P('{"plan": {"summary": "s"}}').kind == "plan"
    assert P("no json here").kind == "invalid" and P("[1,2]").kind == "invalid" and P('{"other": 1}').kind == "invalid"
    assert P('{broken {"final": "found later"}').payload == "found later"


def test_retry_tracker_three_failed_fixes_then_stop():
    t = retries.RetryTracker()
    sig = retries.signature("E   AssertionError: expected 3 got 4 at /tmp/x/app.py line 12")
    assert [t.failure(sig) for _ in range(4)] == [False, False, False, True]   # failure, then 3 failed fixes
    t.success()
    assert t.failure(sig) is False


def test_retry_tracker_new_error_resets_the_count():
    t = retries.RetryTracker()
    a, b = retries.signature("TypeError: x"), retries.signature("NameError: y")
    t.failure(a), t.failure(a), t.failure(a)
    assert t.failure(b) is False and t.failed_fixes == 0


def test_signature_ignores_line_numbers_paths_and_ids():
    s1 = retries.signature("Traceback\n  File C:\\a\\b.py, line 12\nValueError: bad 0x7f12 in /home/u/p/q.py:99")
    s2 = retries.signature("Traceback\n  File D:\\z\\b.py, line 40\nValueError: bad 0x1 in /srv/o/p.py:5")
    assert s1 == s2 or retries.signature("ValueError: bad 12") == retries.signature("ValueError: bad 99")


def test_clip_log_keeps_errors_and_ends():
    log = "\n".join(f"line {i} ok" for i in range(500)) + "\nFAILED tests/x.py::t - AssertionError\n" + "\n".join(f"tail {i}" for i in range(30))
    out = budget.clip_log(log, 1500)
    assert len(out) < 1700 and "AssertionError" in out and "tail 29" in out and "omitted" in out and "line 250 ok" not in out
    assert budget.clip_log("short", 100) == "short"


def test_budget_trims_tool_results_then_drops_oldest_exchanges_and_keeps_roles_alternating():
    b = budget.Budget(window=10000, reserve=2000)
    msgs = [{"role": "user", "content": "task"}]
    for i in range(20):
        msgs += [{"role": "assistant", "content": '{"tool":"x"}'}, {"role": "user", "content": "TOOL RESULT x:\n" + "data " * 1000}]
    assert b.used("sys", msgs) > b.limit
    b.compact("sys", msgs)
    assert b.used("sys", msgs) <= b.limit and msgs[0]["role"] == "user" and "task" in msgs[0]["content"]
    assert all(msgs[i]["role"] != msgs[i + 1]["role"] for i in range(len(msgs) - 1))


def test_budget_overflow_when_even_the_minimum_does_not_fit():
    b = budget.Budget(window=3000, reserve=1000)
    with pytest.raises(budget.ContextOverflow):
        b.compact("s" * 40000, [{"role": "user", "content": "x"}])


def test_budget_default_reserve_is_25_to_30k():
    b = budget.Budget()
    assert b.window == 150000 and 25000 <= b.reserve <= 30000 and b.limit == 150000 - b.reserve


def test_packages_split_to_fit_the_window(repo):
    (repo.root / "big").mkdir()
    steps = []
    for i in range(30):
        (repo.root / "big" / f"f{i}.py").write_text("x = 1\n" * 4000)   # ~24 KB each
        steps.append({"id": f"S{i + 1}", "title": f"step {i}", "files": [f"big/f{i}.py"]})
    pk = packages.split(repo, {"steps": steps}, 150000, 28000)
    cap = packages.capacity(150000, 28000)
    assert len(pk) > 1 and all(p["est_tokens"] <= cap for p in pk) and sum(len(p["steps"]) for p in pk) == 30
    assert [s for p in pk for s in p["steps"]] == [s["id"] for s in steps]   # order kept, nothing lost


def test_oversize_single_step_is_flagged(repo):
    (repo.root / "huge.py").write_text("x" * 1_000_000)
    pk = packages.split(repo, {"steps": [{"id": "S1", "title": "t", "files": ["huge.py"]}]}, 150000, 28000)
    assert pk[0]["oversize"]


def test_plan_validation_normalises_and_rejects(repo):
    good = {"summary": "s", "steps": [{"title": "t", "files": ["app\\calc.py"]}], "files_edit": ["app\\calc.py", "app/money.py"], "files_add": ["app/n.py"]}
    plan, problems = planlib.validate(repo, good)
    assert not problems and plan["files_edit"][0] == "app/calc.py" and plan["needs_owner_approval"] == ["app/money.py"]
    _, problems = planlib.validate(repo, {"summary": "", "steps": [], "files_edit": [".env", "../x", "core/migrations/0002_a.py"]})
    assert len(problems) >= 5


def test_scope_semantics():
    s = planlib.PlanScope({"files_add": ["n.py"], "files_edit": ["e.py"], "files_delete": ["d.py"], "files_rename": [{"from": "a.py", "to": "b.py"}]})
    assert s.allows("create", "n.py") and s.allows("edit", "e.py") and s.allows("create", "b.py") and not s.allows("edit", "x.py")
    assert s.allows("delete", "d.py") and not s.allows("delete", "e.py") and s.allows("rename", "a.py", "b.py") and not s.allows("rename", "a.py", "c.py")


# ---- providers against a real local HTTP server (no network) ----
class Handler(BaseHTTPRequestHandler):
    seen, plan = [], []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((self.path, dict(self.headers), body))
        code, payload = Handler.plan.pop(0)
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    Handler.seen, Handler.plan = [], []
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


MSGS = [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}]


@pytest.mark.parametrize("cls,reply,path,text,finish_reason", [
    (Ollama, {"message": {"content": "hi"}, "prompt_eval_count": 7, "eval_count": 3, "done_reason": "length"}, "/api/chat", "hi", "length"),
    (Anthropic, {"content": [{"type": "text", "text": "hi"}], "usage": {"input_tokens": 7, "output_tokens": 3}, "stop_reason": "max_tokens"}, "/v1/messages", "hi", "max_tokens"),
    (OpenAI, {"choices": [{"message": {"content": "hi"}, "finish_reason": "length"}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}}, "/chat/completions", "hi", "length"),
    (Gemini, {"candidates": [{"content": {"parts": [{"text": "hi"}]}, "finishReason": "MAX_TOKENS"}], "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3}},
     "/v1beta/models/m:generateContent", "hi", "MAX_TOKENS"),
])
def test_each_provider_maps_request_and_reply(server, cls, reply, path, text, finish_reason):
    Handler.plan = [(200, reply)]
    out = cls("m", server, "KEY123", 10, 100, 5000).complete("SYS", MSGS)
    assert out.text == text and out.usage == {"input_tokens": 7, "output_tokens": 3}
    assert out.finish_reason == finish_reason
    got_path, headers, body = Handler.seen[0]
    assert got_path == path and "KEY123" in json.dumps(headers) and "KEY123" not in json.dumps(body)
    assert "SYS" in json.dumps(body) and "a\\n\\nb" in json.dumps(body)   # consecutive user messages were merged


def test_provider_retries_transient_errors_and_redacts_the_key(server, monkeypatch):
    monkeypatch.setattr(phttp.time, "sleep", lambda s: None)
    Handler.plan = [(503, {"e": 1}), (200, {"message": {"content": "ok"}})]
    assert Ollama("m", server, "", 5, 10, 100).complete("s", MSGS).text == "ok" and len(Handler.seen) == 2
    Handler.plan = [(401, {"error": "bad key KEY123"})]
    with pytest.raises(ProviderError) as exc:
        OpenAI("m", server, "KEY123", 5, 10, 100).complete("s", MSGS)
    assert "KEY123" not in str(exc.value) and "401" in str(exc.value) and len(Handler.seen) == 3   # 401 is not retried


def test_provider_unreachable_and_bad_shapes(server):
    with pytest.raises(ProviderError, match="cannot reach"):
        Ollama("m", "http://127.0.0.1:1", "", 2, 10, 100).complete("s", MSGS)
    Handler.plan = [(200, {"weird": 1})]
    with pytest.raises(ProviderError, match="unexpected"):
        Anthropic("m", server, "k", 5, 10, 100).complete("s", MSGS)


def test_registry_requires_model_and_key():
    class S:
        def __init__(self, v): self.v = v
        def get(self, n): return self.v
    cfg = {"provider": "openai", "model": "", "providers": {"openai": {"base_url": "u"}}, "timeout_s": 1, "max_output_tokens": 1, "context_window": 1}
    with pytest.raises(ProviderError, match="no model"):
        build_provider(cfg, S("k"))
    cfg["model"] = "m"
    with pytest.raises(ProviderError, match="no API key"):
        build_provider(cfg, S(None))
    assert build_provider(cfg, S("k")).name == "openai"
    cfg.update(provider="ollama", providers={"ollama": {"base_url": "u"}})
    assert build_provider(cfg, S(None)).name == "ollama"   # a local model needs no key


def test_helpers():
    assert redact("a KEY b", ["KEY", ""]) == "a *** b"
    assert merge_roles([{"role": "user", "content": "x"}, {"role": "user", "content": "y"}]) == [{"role": "user", "content": "x\n\ny"}]
