"""WealthFlow starts the ComfyUI server itself: settings saved -> server up -> image generated -> switched off -> server gone.
Uses a real child process (fake_comfy_server.py) and the real provider, tool and settings code."""

import json
import os
import shutil
import tempfile
import time

from django.test import override_settings

from core.models import AIAttachment, AppSettings
from core.services.ai.image_generation import generate_image, image_generation_available, test_connection
from core.services.ai.image_generation.server import manager, state, stop_server
from core.tests.ai.test_ai_image_generation import ImageBase, make_user
from core.tests.ai.test_ai_image_server import command, free_port


class ManagedServerFlowTests(ImageBase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(BASE_DIR=self.tmp)
        self.override.enable()
        manager._child = None
        self.port = free_port()
        self.admin = make_user("srv-admin", sysadmin=True)
        self.client.force_login(self.admin)

    def tearDown(self):
        stop_server()
        saved = state.read_state()
        if saved and state.pid_alive(saved["pid"]):
            state.kill_tree(saved["pid"], True)
        self.override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def settings_body(self, **over):
        body = {"image_gen_enabled": True, "image_gen_provider": "comfyui", "image_gen_model": "flux-2-klein-4b.safetensors",
                "image_gen_endpoint": f"http://127.0.0.1:{self.port}", "image_gen_api_key": "", "image_gen_start_command": command()}
        return {**body, **over}

    def post(self, **over):
        return self.client.post("/api/settings/ai/", json.dumps(self.settings_body(**over)), content_type="application/json")

    def wait_for_server(self, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            saved = state.read_state()
            if saved and state.is_same_process(saved):
                return saved["pid"]
            time.sleep(0.2)
        self.fail("the server was not started")

    def test_enabling_starts_the_server_generating_uses_it_and_disabling_stops_it(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertTrue(image_generation_available())
        pid = self.wait_for_server()                                       # started in the background by the settings save
        out = generate_image(self.admin, {"prompt": "a lighthouse"})
        self.assertTrue(out.get("ok"), out)                                # text-to-image through the managed server
        self.assertEqual(AIAttachment.objects.get(pk=out["image_id"]).mime, "image/png")
        self.assertEqual(state.read_state()["pid"], pid)                   # reused, not restarted
        edit = generate_image(self.admin, {"prompt": "darker", "source_image_id": out["image_id"]})
        self.assertTrue(edit.get("ok") and edit["edited"], edit)
        self.assertIn("started by WealthFlow", test_connection())
        self.assertEqual(self.post(image_gen_enabled=False).status_code, 200)
        deadline = time.monotonic() + 15
        while state.pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(state.pid_alive(pid))                             # switched off -> the server WealthFlow started is stopped
        self.assertIsNone(state.read_state())

    def test_first_generation_starts_the_server_when_nothing_warmed_it_up(self):
        from core.services.ai.image_generation import save_image_settings
        save_image_settings(self.settings_body())                          # saved without the view: no warm start
        self.assertIsNone(state.read_state())
        out = generate_image(self.admin, {"prompt": "a lighthouse"})
        self.assertTrue(out.get("ok"), out)
        self.assertIsNotNone(state.read_state())

    def test_a_server_that_crashes_is_reported_and_chat_keeps_working(self):
        from core.services.ai.image_generation import save_image_settings
        save_image_settings(self.settings_body(image_gen_start_command=command("--exit-code 3")))
        out = generate_image(self.admin, {"prompt": "a lighthouse"})
        self.assertIn("exit code 3", out["error"])
        self.assertIn("boom: cannot load model", out["error"])
        self.assertEqual(AIAttachment.objects.count(), 0)

    def test_saving_a_missing_program_is_refused(self):
        res = self.post(image_gen_start_command="/no/such/program --port {port}")
        self.assertEqual(res.status_code, 400)
        self.assertIn("not found", res.json()["error"])
        self.assertFalse(AppSettings.objects.filter(key="image_gen_start_command", owner=None).exclude(value="").exists())

    def test_without_a_start_command_nothing_is_started_and_an_external_server_is_used(self):
        from core.services.ai.image_generation import save_image_settings
        save_image_settings(self.settings_body(image_gen_start_command=""))
        out = generate_image(self.admin, {"prompt": "x"})
        self.assertIn("error", out)                                        # nothing listening, nothing started
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "runtime", "image_server", "state.json")))

    def test_test_connection_uses_the_start_command_typed_in_the_form_before_saving(self):
        body = {k: v for k, v in self.settings_body().items() if k != "image_gen_enabled"}
        res = self.client.post("/api/settings/ai/image-generation/test/", json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("started by WealthFlow", res.json()["detail"])
        self.assertIsNotNone(state.read_state())                           # started from the unsaved form value
        stop_server()                                                      # a server that already answers needs no command at all
        bad = self.client.post("/api/settings/ai/image-generation/test/", json.dumps({**body, "image_gen_start_command": "/no/such/program"}), content_type="application/json")
        self.assertEqual(bad.status_code, 502)
        self.assertIn("not found", bad.json()["error"])
