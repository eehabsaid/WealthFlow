import os
import threading
import time

import pytest

from ..core import fsutil
from ..core.project import PathError, Project, matches, norm


@pytest.mark.parametrize("bad", ["/etc/passwd", "C:\\Windows\\x", "C:/x", "\\\\server\\share\\f", "../x", "a/../../x", "a/b:stream", "con.txt",
                                 "a/NUL", "a/file.", "~/x", "", ".", "a/aux.py", "a/x\0y"])
def test_norm_rejects_unsafe_paths(bad):
    with pytest.raises(PathError):
        norm(bad)


def test_norm_accepts_windows_separators():
    assert norm("app\\sub\\f.py") == "app/sub/f.py"
    assert norm("./a//b.py") == "a/b.py"
    assert norm("console.js") == "console.js"


def test_resolve_blocks_symlink_escape(repo, tmp_path):
    try:
        os.symlink(tmp_path, repo.root / "link")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(PathError):
        repo.resolve("link/x.py")


def test_matches_is_case_insensitive_and_checks_basename():
    assert matches("Core/Salary/X.py", [{"pattern": "core/salary/*", "reason": "r"}]) == "r"
    assert matches("sub/dir/.env", [".env"]) == ".env"
    assert matches("a/b.py", ["c/*"]) is None


def test_project_reasons_and_config_merge(repo):
    assert repo.protected_reason("app/money.py") == "balances"
    assert repo.forbidden_reason("app/migrations/0001_x.py")
    assert repo.forbidden_reason(".git/config")
    assert repo.secret_reason(".env")
    assert repo.test_module("app/calc.py") == "tests/test_calc.py"
    assert repo.config["secret_files"]   # default kept although config.json did not set it
    assert Project(repo.root / "nowhere").config["max_file_lines"] == 200


def test_atomic_write_new_overwrite_and_no_temp_left(tmp_path):
    target = tmp_path / "d" / "f.txt"
    fsutil.atomic_write(target, b"one")
    fsutil.atomic_write(target, b"two")
    assert target.read_bytes() == b"two"
    assert [p.name for p in target.parent.iterdir()] == ["f.txt"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes")
def test_atomic_write_keeps_mode(tmp_path):
    target = tmp_path / "f.sh"
    target.write_bytes(b"x")
    target.chmod(0o750)
    fsutil.atomic_write(target, b"y")
    assert target.stat().st_mode & 0o777 == 0o750


def test_atomic_write_failure_leaves_target_intact(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_bytes(b"keep")
    monkeypatch.setattr(fsutil, "replace_retry", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        fsutil.atomic_write(target, b"new")
    assert target.read_bytes() == b"keep"
    assert [p.name for p in tmp_path.iterdir()] == ["f.txt"]


def test_replace_retry_waits_out_windows_permission_errors(tmp_path, monkeypatch):
    calls = []
    real = os.replace

    def flaky(src, dst):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("held by antivirus")
        real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    (tmp_path / "a").write_text("x")
    fsutil.replace_retry(tmp_path / "a", tmp_path / "b")
    assert len(calls) == 3 and (tmp_path / "b").exists()


def test_crlf_roundtrip_and_binary_detection():
    text, crlf = fsutil.decode(b"a\r\nb\r\n")
    assert (text, crlf) == ("a\nb\n", True)
    assert fsutil.encode(text, crlf) == b"a\r\nb\r\n"
    assert fsutil.decode(b"a\nb\n")[1] is False
    with pytest.raises(UnicodeDecodeError):
        fsutil.decode(b"\xff\xfe\x00bin")


def test_lock_excludes_second_holder_and_releases(tmp_path):
    with fsutil.file_lock(tmp_path, "k"):
        with pytest.raises(fsutil.LockTimeout):
            with fsutil.file_lock(tmp_path, "k", timeout=0.2):
                pass
    with fsutil.file_lock(tmp_path, "k", timeout=0.2):
        pass
    assert list(tmp_path.iterdir()) == []


def test_stale_lock_is_broken(tmp_path):
    lock = tmp_path / (__import__("hashlib").sha1(b"k").hexdigest()[:24] + ".lock")
    lock.write_text("dead")
    os.utime(lock, (time.time() - 1000, time.time() - 1000))
    with fsutil.file_lock(tmp_path, "k", timeout=1, stale=60):
        pass


def test_lock_many_two_writers_do_not_deadlock(tmp_path):
    done = []

    def worker(keys):
        with fsutil.lock_many(tmp_path, keys, timeout=10):
            time.sleep(0.05)
            done.append(1)

    threads = [threading.Thread(target=worker, args=(k,)) for k in (["a", "b"], ["b", "a"])]
    [t.start() for t in threads]
    [t.join(15) for t in threads]
    assert len(done) == 2
