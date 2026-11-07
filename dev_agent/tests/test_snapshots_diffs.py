import pytest

from ..core.project import PathError
from ..ledger.ledger import Ledger
from ..service import diffs
from ..tools import call


def edit(ctx, *e):
    return call(ctx, "edit_files", {"edits": list(e)})


def test_original_is_saved_before_the_first_write_and_kept_across_later_edits(ctx):
    call(ctx, "read_file", {"path": "app/calc.py"})
    edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a - b"}]})
    edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a - b", "new": "a * b"}]})
    known, original = ctx.ledger.original("app/calc.py")
    assert known and original == b"def add(a, b):\n    return a + b\n"
    out = diffs.file_diff(ctx.ledger, ctx.project, "app/calc.py")
    assert "-    return a + b" in out["diff"] and "+    return a * b" in out["diff"] and out["state"] == "written" and out["existed_before"]
    assert Ledger.load(ctx.project, ctx.ledger.id).original("app/calc.py")[1] == original     # survives a restart


def test_new_file_has_no_original_and_diff_shows_it_added(ctx):
    edit(ctx, {"path": "app/new.py", "content": "X = 1\n"})
    out = diffs.file_diff(ctx.ledger, ctx.project, "app/new.py")
    assert out["known_original"] and not out["existed_before"] and out["diff"].startswith("--- /dev/null") and "+X = 1" in out["diff"]


def test_deleted_file_diff_and_original_bytes(ctx):
    call(ctx, "delete_file", {"path": "app/old.py"})
    out = diffs.file_diff(ctx.ledger, ctx.project, "app/old.py")
    assert out["state"] == "deleted" and not out["exists_now"] and "-OLD = 1" in out["diff"]
    assert diffs.original_bytes(ctx.ledger, ctx.project, "app/old.py") == b"OLD = 1\n" and diffs.current_bytes(ctx.ledger, ctx.project, "app/old.py") is None


def test_renamed_file_original_comes_from_the_old_path(ctx):
    assert call(ctx, "rename_file", {"from": "app/util.py", "to": "app/utils.py"})["ok"]
    out = diffs.file_diff(ctx.ledger, ctx.project, "app/utils.py")
    assert out["renamed_from"] == "app/util.py" and out["known_original"] and out["diff"] == ""
    edit(ctx, {"path": "app/utils.py", "replacements": [{"old": "out = 0", "new": "out = 1"}]})
    assert "+    out = 1" in diffs.file_diff(ctx.ledger, ctx.project, "app/utils.py")["diff"]


def test_crlf_original_is_compared_without_noise(ctx):
    (ctx.project.root / "app/calc.py").write_bytes(b"def add(a, b):\r\n    return a + b\r\n")
    call(ctx, "read_file", {"path": "app/calc.py"})
    edit(ctx, {"path": "app/calc.py", "replacements": [{"old": "a + b", "new": "a - b"}]})
    d = diffs.file_diff(ctx.ledger, ctx.project, "app/calc.py")["diff"].splitlines()
    assert sum(1 for l in d if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))) == 2


def test_only_files_of_the_task_can_be_read_through_the_diff_api(ctx):
    for path in ("app/util.py", ".env", "../x", "C:\\Windows\\win.ini", "db.sqlite3", ".git/config"):
        with pytest.raises((diffs.NotInTask, PathError)):
            diffs.file_diff(ctx.ledger, ctx.project, path)
        with pytest.raises((diffs.NotInTask, PathError)):
            diffs.original_bytes(ctx.ledger, ctx.project, path)


def test_binary_files_are_flagged_not_dumped(ctx):
    ctx.scope.write.add("app/blob.bin")
    ctx.ledger.snapshot_original("app/blob.bin", b"\x00\x01\x02")
    ctx.ledger.record_file("app/blob.bin", "written", None, "x", "P1")
    (ctx.project.root / "app/blob.bin").write_bytes(b"\x00\x09")
    out = diffs.file_diff(ctx.ledger, ctx.project, "app/blob.bin")
    assert out["binary"] and out["diff"] == ""
