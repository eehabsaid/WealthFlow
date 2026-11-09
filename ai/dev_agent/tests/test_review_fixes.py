"""Regression tests for bugs found in the M3 review of the existing code."""

import json
import os
import subprocess
import sys
import time

import pytest

from ai.dev_agent.core import fsutil
from ai.dev_agent.service.events import EventLog


def dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_event_log_after_a_torn_last_line_keeps_new_events_readable(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"seq": 1, "type": "a"}) + "\n" + '{"seq": 2, "type": "b", "mess', encoding="utf-8")   # the process died mid-write
    log = EventLog(path)
    assert [e["seq"] for e in log.after(0)] == [1]
    log.append({"type": "c"})
    log.append({"type": "d"})
    again = EventLog(path)                                          # next server start
    assert [e["type"] for e in again.after(0)] == ["a", "c", "d"] and [e["seq"] for e in again.after(0)] == [1, 2, 3]


def test_event_log_with_invalid_utf8_still_loads(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_bytes(json.dumps({"seq": 1, "type": "a"}).encode() + b"\n\xff\xfe broken\n")
    assert [e["type"] for e in EventLog(path).after(0)] == ["a"]


def test_a_lock_left_by_a_crashed_process_is_broken_at_once(tmp_path):
    first = {}
    with fsutil.file_lock(tmp_path, "ledger:x"):
        lock = next(tmp_path.glob("*.lock"))
        first["text"] = lock.read_text()
    lock.write_text(f"{dead_pid()} {time.time()}")                 # as if the process had crashed inside the with-block
    started = time.monotonic()
    with fsutil.file_lock(tmp_path, "ledger:x", timeout=5):
        pass
    assert time.monotonic() - started < 2 and first["text"].split()[0] == str(os.getpid())


def test_a_lock_held_by_a_live_process_is_respected(tmp_path):
    with fsutil.file_lock(tmp_path, "k"):
        with pytest.raises(fsutil.LockTimeout):
            with fsutil.file_lock(tmp_path, "k", timeout=0.3):
                pass


def test_an_unreadable_lock_file_falls_back_to_the_age_rule(tmp_path):
    with fsutil.file_lock(tmp_path, "k"):
        lock = next(tmp_path.glob("*.lock"))
        lock.write_text("garbage")
        with pytest.raises(fsutil.LockTimeout):
            with fsutil.file_lock(tmp_path, "k", timeout=0.3):
                pass
        os.utime(lock, (time.time() - 1000, time.time() - 1000))
        with fsutil.file_lock(tmp_path, "k", timeout=2):
            pass


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_new_files_get_the_normal_permissions_without_touching_the_process_umask(tmp_path):
    before = os.umask(0o022)
    try:
        fsutil.atomic_write(tmp_path / "f.txt", b"x")
        assert os.umask(0o022) == 0o022                                      # unchanged by atomic_write
        assert (tmp_path / "f.txt").stat().st_mode & 0o777 == 0o666 & ~fsutil.UMASK
    finally:
        os.umask(before)
