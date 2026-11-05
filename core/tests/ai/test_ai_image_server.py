"""Managed image server: real processes (a fake ComfyUI), start / readiness / duplicate prevention / stop / error reporting."""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings

from core.services.ai.image_generation.server import ServerError, ensure_running, manager, process, state, stop_server

FAKE = os.path.join(os.path.dirname(__file__), "fake_comfy_server.py")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def command(extra: str = "") -> str:
    return f'"{sys.executable}" "{FAKE}" --port {{port}} {extra}'.strip()


class ServerCase(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(BASE_DIR=self.tmp)
        self.override.enable()
        self.port = free_port()
        self.endpoint = f"http://127.0.0.1:{self.port}"
        self.key = state.endpoint_key(self.endpoint)
        manager._children.clear()

    def tearDown(self):
        stop_server(self.endpoint)
        saved = state.read_state(self.key)
        if saved and state.pid_alive(saved["pid"]) and state.is_same_process(saved):
            state.kill_tree(saved["pid"], True)
        self.override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def probe(self) -> bool:
        try:
            return requests.get(self.endpoint + "/system_stats", timeout=1).status_code == 200
        except requests.RequestException:
            return False

    def starts(self) -> int:
        with open(state.log_path(self.key), encoding="utf-8") as fh:
            return fh.read().count("=== starting")


class LifecycleTests(ServerCase):
    def test_starts_waits_until_ready_and_reuses_the_running_server(self):
        note = ensure_running(command("--delay 1"), self.endpoint, self.probe, timeout=30)
        self.assertIn("started by WealthFlow", note)
        pid = state.read_state(self.key)["pid"]
        self.assertTrue(state.pid_alive(pid) and self.probe())
        self.assertIn("already running", ensure_running(command(), self.endpoint, self.probe, timeout=5).lower().replace("is running", "already running"))
        self.assertEqual(state.read_state(self.key)["pid"], pid)
        self.assertEqual(self.starts(), 1)

    def test_concurrent_requests_start_exactly_one_server(self):
        errors = []

        def go():
            try:
                ensure_running(command("--delay 2"), self.endpoint, self.probe, timeout=30)
            except Exception as exc:   # pragma: no cover - reported by the assertion below
                errors.append(exc)
        threads = [threading.Thread(target=go) for _ in range(4)]
        [t.start() for t in threads]
        [t.join(60) for t in threads]
        self.assertEqual(errors, [])
        self.assertEqual(self.starts(), 1)

    def test_a_server_still_loading_after_a_timeout_is_adopted_not_duplicated(self):
        with self.assertRaises(ServerError) as ctx:      # the first caller gives up while the models are still loading
            ensure_running(command("--delay 6"), self.endpoint, self.probe, timeout=2)
        self.assertIn("still starting", str(ctx.exception))
        pid = state.read_state(self.key)["pid"]
        manager._children.clear()                            # the next caller (another Django process) only has the state file
        note = ensure_running(command("--delay 6"), self.endpoint, self.probe, timeout=30)
        self.assertEqual(state.read_state(self.key)["pid"], pid)
        self.assertEqual(self.starts(), 1)
        self.assertIn(str(pid), note)
        self.assertTrue(stop_server(self.endpoint))                   # a verified earlier server can still be stopped without the Popen object

    def test_stop_ends_the_process_tree_and_clears_state(self):
        ensure_running(command(), self.endpoint, self.probe, timeout=30)
        pid = state.read_state(self.key)["pid"]
        self.assertTrue(stop_server(self.endpoint))
        self.assertFalse(state.pid_alive(pid))
        self.assertFalse(self.probe())
        self.assertIsNone(state.read_state(self.key))
        self.assertFalse(stop_server(self.endpoint))

    def test_a_server_not_started_by_wealthflow_is_never_stopped(self):
        external = subprocess.Popen([sys.executable, FAKE, "--port", str(self.port)])
        try:
            deadline = time.monotonic() + 10
            while not self.probe() and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertIn("is running", ensure_running(command(), self.endpoint, self.probe, timeout=5))
            self.assertFalse(stop_server(self.endpoint))
            self.assertIsNone(external.poll())
            self.assertEqual(os.path.exists(state.log_path(self.key)), False)   # nothing was spawned
        finally:
            external.kill()
            external.wait()

    def test_a_recycled_pid_is_never_killed(self):
        state.write_state(self.key, {"pid": os.getpid(), "start_time": 1.0, "command": "x", "endpoint": self.endpoint})
        self.assertFalse(state.is_same_process(state.read_state(self.key)))
        self.assertFalse(stop_server(self.endpoint))          # would terminate this very test process if the guard failed
        self.assertIsNone(state.read_state(self.key))

    def test_stale_state_of_a_dead_process_is_replaced(self):
        state.write_state(self.key, {"pid": 2**22 + 12345, "start_time": 1.0, "command": "x", "endpoint": self.endpoint})
        self.assertIn("started by WealthFlow", ensure_running(command(), self.endpoint, self.probe, timeout=30))
        self.assertEqual(self.starts(), 1)


class TwoServersTests(ServerCase):
    """The E2E hang: another endpoint's server (your real ComfyUI) must never be mistaken for this one's."""

    def test_another_endpoints_server_is_neither_waited_for_nor_adopted_nor_stopped(self):
        real_port = free_port()
        real = f"http://127.0.0.1:{real_port}"
        def real_probe():
            try:
                return requests.get(real + "/system_stats", timeout=1).status_code == 200
            except requests.RequestException:
                return False
        ensure_running(command(), real, real_probe, timeout=30)
        real_state = state.read_state(state.endpoint_key(real))
        started = time.monotonic()
        note = ensure_running(command(), self.endpoint, self.probe, timeout=30)       # a different port: its own server, quickly
        self.assertLess(time.monotonic() - started, 20)
        self.assertIn("started by WealthFlow", note)
        self.assertNotEqual(state.read_state(self.key)["pid"], real_state["pid"])
        self.assertTrue(stop_server(self.endpoint))
        self.assertTrue(state.pid_alive(real_state["pid"]))                         # the other server is untouched
        self.assertTrue(stop_server(real))

    def test_a_state_file_from_before_keying_is_adopted_only_for_its_own_endpoint(self):
        legacy = os.path.join(state.runtime_dir(), "state.json")
        with open(legacy, "w", encoding="utf-8") as fh:
            fh.write('{"pid": %d, "start_time": 1.0, "command": "x", "endpoint": "http://127.0.0.1:1"}' % os.getpid())
        self.assertIsNone(state.read_state(self.key))                               # another endpoint: not ours
        self.assertTrue(os.path.exists(legacy))
        self.assertIsNotNone(state.read_state(state.endpoint_key("http://127.0.0.1:1")))
        self.assertFalse(os.path.exists(legacy))                                    # migrated to the keyed name


class ErrorTests(ServerCase):
    def test_a_crash_during_startup_reports_exit_code_and_server_output(self):
        with self.assertRaises(ServerError) as ctx:
            ensure_running(command("--exit-code 3"), self.endpoint, self.probe, timeout=30)
        self.assertIn("exit code 3", str(ctx.exception))
        self.assertIn("boom: cannot load model", str(ctx.exception))
        self.assertIsNone(state.read_state(self.key))

    def test_a_port_held_by_something_else_times_out_with_a_clear_message(self):
        with socket.socket() as blocker:
            blocker.bind(("127.0.0.1", self.port))
            blocker.listen(1)
            with self.assertRaises(ServerError) as ctx:
                ensure_running(command("--port-clash"), self.endpoint, lambda: False, timeout=3)
        self.assertTrue("still starting" in str(ctx.exception) or "stopped while starting" in str(ctx.exception))

    def test_command_problems_are_reported_before_anything_starts(self):
        with self.assertRaises(ServerError):
            ensure_running("/no/such/program --port {port}", self.endpoint, self.probe, timeout=5)
        with self.assertRaises(ServerError):
            ensure_running('"unbalanced', self.endpoint, self.probe, timeout=5)
        with self.assertRaises(ServerError):
            ensure_running("   ", self.endpoint, self.probe, timeout=5)
        self.assertFalse(os.path.exists(state.log_path(self.key)))

    def test_host_and_port_come_from_the_api_url(self):
        args = process.build_args('"C:\\\\Comfy\\\\python.exe" main.py --listen {host} --port {port}', "http://10.0.0.5:9000")
        self.assertEqual(args[-4:], ["--listen", "10.0.0.5", "--port", "9000"])
        self.assertEqual(process.build_args("py main.py --port {port}", "127.0.0.1")[-1], "8188")

    def test_windows_style_commands_lose_their_quotes_and_keep_backslashes(self):
        cmd = '"D:\\Comfy App\\.venv\\Scripts\\python.exe" "D:\\Comfy App\\main.py" --extra-model-paths-config="D:\\AI Models\\x.yaml" --port {port}'
        with patch.object(state, "IS_WINDOWS", True):
            args = process.build_args(cmd, "http://127.0.0.1:8188")
            self.assertEqual(args, ["D:\\Comfy App\\.venv\\Scripts\\python.exe", "D:\\Comfy App\\main.py",
                                    "--extra-model-paths-config=D:\\AI Models\\x.yaml", "--port", "8188"])
            with self.assertRaises(ServerError):
                process.build_args('"D:\\unbalanced', "http://127.0.0.1:8188")
