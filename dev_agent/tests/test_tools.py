from ..core import fsutil
from ..tools import call


def read(ctx, path):
    return call(ctx, "read_file", {"path": path})


def edit(ctx, *edits):
    return call(ctx, "edit_files", {"edits": list(edits)})


def states(res):
    return {f["path"]: f["state"] for f in res["files"]}


def test_read_file_numbers_lines_and_records_sha(ctx):
    res = read(ctx, "app/calc.py")
    assert res["total_lines"] == 3 and res["text"].startswith("1\tdef add") and ctx.seen["app/calc.py"] == res["sha"]


def test_secret_git_and_outside_reads_are_refused(ctx):
    for path in (".env", ".git/config", "../x", "C:\\x", "app/missing.py"):
        assert "error" in read(ctx, path)


def test_multi_file_edit_writes_all_and_reports_state(ctx):
    read(ctx, "app/calc.py")
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a + b + 0"}]},
               {"path": "app/new.py", "content": "X = 1\n"})
    assert res["ok"] and states(res) == {"app/calc.py": "written", "app/new.py": "written"}
    assert "a + b + 0" in (ctx.project.root / "app/calc.py").read_text()
    assert ctx.ledger.data["files"]["app/new.py"]["state"] == "written"


def test_edit_is_all_or_nothing_when_one_file_is_rejected(ctx):
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a * b"}]},
               {"path": "app/calc.py".replace("calc", "other_not_in_plan"), "content": "x = 1\n"})
    assert not res["ok"] and "nothing was written" in res["error"]
    assert "a + b" in (ctx.project.root / "app/calc.py").read_text()
    assert states(res)["app/calc.py"] == "unchanged"


def test_old_text_must_match_exactly_once(ctx):
    (ctx.project.root / "app/calc.py").write_text("x = 1\nx = 1\n")
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "x = 1", "new": "x = 2"}]})
    assert not res["ok"] and "2 times" in res["files"][0]["detail"]
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "nope", "new": "x"}]})
    assert "0 times" in res["files"][0]["detail"]


def test_sha_conflict_after_read_is_detected(ctx):
    read(ctx, "app/calc.py")
    (ctx.project.root / "app/calc.py").write_text("def add(a, b):\n    return 0\n")   # someone else edits it
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "return 0", "new": "return 1"}]})
    assert not res["ok"] and "sha mismatch" in res["files"][0]["detail"]
    assert "return 0" in (ctx.project.root / "app/calc.py").read_text()


def test_explicit_expect_sha(ctx):
    res = edit(ctx, {"path": "app/calc.py", "expect_sha": "0" * 64, "replacements": [{"old": "a + b", "new": "a - b"}]})
    assert not res["ok"] and "conflict" in res["files"][0]["detail"]


def test_concurrent_change_between_validation_and_write_aborts_everything(ctx, monkeypatch):
    from ..tools import edit as edit_mod
    read(ctx, "app/calc.py")
    real = edit_mod._commit

    def sneaky(c, preps):
        (c.project.root / "app/calc.py").write_text("def add(a, b):\n    return 99\n")   # lands after validation
        return real(c, preps)

    monkeypatch.setattr(edit_mod, "_commit", sneaky)
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a - b"}]}, {"path": "app/new.py", "content": "X = 1\n"})
    assert not res["ok"] and "concurrently" in res["error"]
    assert not (ctx.project.root / "app/new.py").exists() and "return 99" in (ctx.project.root / "app/calc.py").read_text()
    assert states(res) == {"app/calc.py": "conflict", "app/new.py": "unchanged"}


def test_partial_write_failure_rolls_back_and_reports_exact_state(ctx, monkeypatch):
    from ..tools import edit as edit_mod
    read(ctx, "app/calc.py")
    real, calls = fsutil.atomic_write, []

    def flaky(path, data):
        calls.append(str(path))
        if str(path).endswith("new.py"):
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(edit_mod.fsutil, "atomic_write", flaky)
    res = edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a - b"}]}, {"path": "app/new.py", "content": "X = 1\n"})
    monkeypatch.setattr(edit_mod.fsutil, "atomic_write", real)
    assert not res["ok"] and "disk full" in res["error"]
    assert states(res) == {"app/calc.py": "rolled_back", "app/new.py": "failed"}
    assert "a + b" in (ctx.project.root / "app/calc.py").read_text() and not (ctx.project.root / "app/new.py").exists()


def test_rollback_does_not_clobber_foreign_changes(ctx):
    from ..tools.edit import Prep, _rollback
    path = ctx.project.root / "app/calc.py"
    p = Prep("app/calc.py", path, b"old", b"new", fsutil.sha(b"old"), fsutil.sha(b"new"))
    path.write_bytes(b"someone else's work")
    _rollback(p)
    assert p.state == "rollback_failed" and path.read_bytes() == b"someone else's work"


def test_syntax_errors_in_python_and_json_are_refused(ctx):
    assert "would not parse" in edit(ctx, {"path": "app/new.py", "content": "def (:\n"})["files"][0]["detail"]
    assert not (ctx.project.root / "app/new.py").exists()
    ctx.scope.write.add("a.json")
    assert "would not parse" in edit(ctx, {"path": "a.json", "content": "{bad"})["files"][0]["detail"]


def test_existing_file_needs_overwrite_flag_and_dupes_are_rejected(ctx):
    assert "overwrite" in edit(ctx, {"path": "app/calc.py", "content": "x = 1\n"})["files"][0]["detail"]
    res = edit(ctx, {"path": "app/new.py", "content": "A = 1\n"}, {"path": "app\\new.py", "content": "B = 1\n"})
    assert "twice" in str(res["files"])


def test_crlf_files_keep_their_line_endings(ctx):
    path = ctx.project.root / "app/calc.py"
    path.write_bytes(b"def add(a, b):\r\n    return a + b\r\n")
    read(ctx, "app/calc.py")
    assert edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a - b"}]})["ok"]
    assert path.read_bytes() == b"def add(a, b):\r\n    return a - b\r\n"


def test_binary_file_is_refused(ctx):
    (ctx.project.root / "app/calc.py").write_bytes(b"\xff\xfe\x00\x01")
    assert not edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a", "new": "b"}]})["ok"]


def test_identical_content_is_reported_unchanged(ctx):
    res = edit(ctx, {"path": "app/calc.py", "content": "def add(a, b):\n    return a + b\n", "overwrite": True})
    assert res["ok"] and states(res) == {"app/calc.py": "unchanged"}


def test_scope_guards_files_outside_the_plan_and_forbidden_files(ctx):
    for path in ("app/util_not_listed.py", ".env", "core/migrations/0001_x.py", "db.sqlite3", ".git/config"):
        res = edit(ctx, {"path": path, "content": "x = 1\n"})
        assert not res["ok"] and "rejected" in str(res["files"]) or "error" in res


def test_protected_file_needs_approval_and_asks_once(ctx):
    ctx.approver.answer = False
    res = edit(ctx, {"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]})
    assert not res["ok"] and "PROTECTED" in res["files"][0]["detail"] and (ctx.project.root / "app/money.py").read_text() == "BALANCE = 1\n"
    ctx.approver.answer = True
    assert edit(ctx, {"path": "app/money.py", "replacements": [{"old": "1", "new": "2"}]})["ok"]
    edit(ctx, {"path": "app/money.py", "replacements": [{"old": "2", "new": "3"}]})
    assert len([a for a in ctx.approver.asked if "money" in a[1]]) == 2   # one refusal, one approval; the approval is remembered


def test_readonly_phase_has_no_mutating_tools(ctx):
    ctx.readonly = True
    assert "not available while planning" in call(ctx, "edit_files", {"edits": []})["error"]
    assert "not available" in call(ctx, "delete_file", {"path": "app/old.py"})["error"]
