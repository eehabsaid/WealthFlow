import os

import pytest

from ai.dev_agent.tools import call


def read(ctx, path):
    return call(ctx, "read_file", {"path": path})


def test_delete_only_when_listed(ctx):
    assert "not listed" in call(ctx, "delete_file", {"path": "app/calc.py"})["error"] or "not in" in call(ctx, "delete_file", {"path": "app/calc.py"})["error"]
    assert (ctx.project.root / "app/calc.py").exists()
    res = call(ctx, "delete_file", {"path": "app/old.py"})
    assert res["state"] == "deleted" and not (ctx.project.root / "app/old.py").exists()
    assert ctx.ledger.data["files"]["app/old.py"]["state"] == "deleted"


def test_delete_conflict_when_file_changed_since_read(ctx):
    ctx.scope.delete.add("app/calc.py")
    read(ctx, "app/calc.py")
    (ctx.project.root / "app/calc.py").write_text("changed\n")
    assert "conflict" in call(ctx, "delete_file", {"path": "app/calc.py"})["error"]
    assert (ctx.project.root / "app/calc.py").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only attribute")
def test_delete_handles_windows_readonly(ctx):
    os.chmod(ctx.project.root / "app/old.py", 0o444)
    assert call(ctx, "delete_file", {"path": "app/old.py"})["ok"]


def test_rename_listed_pair_reports_importers_and_never_overwrites(ctx):
    res = call(ctx, "rename_file", {"from": "app/util.py", "to": "app/utils.py"})
    assert res["ok"] and not (ctx.project.root / "app/util.py").exists() and (ctx.project.root / "app/utils.py").exists()
    assert ctx.ledger.data["files"]["app/util.py"]["state"] == "renamed"
    (ctx.project.root / "app/utils2.py").write_text("x = 1\n")
    ctx.scope.rename["app/utils.py"] = "app/utils2.py"
    ctx.scope.write.add("app/utils2.py")
    assert "already exists" in call(ctx, "rename_file", {"from": "app/utils.py", "to": "app/utils2.py"})["error"]


def test_rename_not_in_plan_is_refused(ctx):
    assert "error" in call(ctx, "rename_file", {"from": "app/calc.py", "to": "app/calc2.py"})
    assert (ctx.project.root / "app/calc.py").exists()


def test_grep_skips_secrets_and_excluded_folders(ctx):
    (ctx.project.root / "node_modules").mkdir()
    (ctx.project.root / "node_modules/x.js").write_text("KEY=secret\n")
    assert call(ctx, "grep", {"pattern": "secret"})["matches"] == []
    assert any("calc.py:1" in m for m in call(ctx, "grep", {"pattern": "def add", "glob": "*.py"})["matches"])
    assert "bad regex" in call(ctx, "grep", {"pattern": "("})["error"]


def test_plan_check_reports_protected_callers_and_tests(ctx):
    res = call(ctx, "plan_check", {"files": ["app/calc.py", "app/money.py"]})
    rows = {r["file"]: r for r in res["files"]}
    assert rows["app/money.py"]["protected"] == "balances" and "app/money.py" in res["needs_owner_approval"]
    assert "app/util.py" in rows["app/calc.py"]["callers"] and res["tests_to_run"] == ["tests/test_calc.py"]


def test_search_index_finds_symbols(ctx):
    assert call(ctx, "search_index", {"query": "total util"})["results"][0]["path"] == "app/util.py"


def test_unknown_tool_and_bad_args(ctx):
    assert "unknown tool" in call(ctx, "format_disk", {})["error"]
    assert "JSON object" in call(ctx, "read_file", [])["error"]
    assert "error" in call(ctx, "read_file", {})


def test_note_proposal_is_recorded(ctx):
    assert call(ctx, "note_proposal", {"path": "app/money.py", "text": "use Decimal"})["ok"]
    assert ctx.ledger.data["proposals"][0]["path"] == "app/money.py"
