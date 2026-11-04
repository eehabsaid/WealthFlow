"""Image generation over HTTP: owner-scoped serving / download of generated images, AI settings round-trip, connection test."""

import json
from unittest.mock import patch

from core.services.ai.image_generation import generate_image, image_generation_available
from core.services.ai.image_generation.providers import ImageProviderError
from core.tests.ai.test_ai_image_generation import CFG, ImageBase, make_user


class ViewTests(ImageBase):
    URL = "/api/financial-advisor/ai/attachments/{}/"

    def test_serve_and_download_are_owner_only(self):
        self.enable_fake()
        pk = generate_image(self.user, {"prompt": "a cat"})["image_id"]
        self.client.force_login(self.user)
        shown = self.client.get(self.URL.format(pk))
        self.assertEqual((shown.status_code, shown["Content-Type"], shown["Content-Disposition"]), (200, "image/png", "inline"))
        self.assertIn("attachment", self.client.get(self.URL.format(pk) + "?download=1")["Content-Disposition"])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.URL.format(pk)).status_code, 404)
        self.client.logout()
        self.assertIn(self.client.get(self.URL.format(pk)).status_code, (401, 302, 403))

    def test_ai_settings_roundtrip_and_connection_test(self):
        admin = make_user("img-admin", sysadmin=True)
        self.client.force_login(admin)
        body = self.client.get("/api/settings/ai/").json()
        self.assertFalse(body["image_gen_enabled"])
        self.assertIn("comfyui", [p["key"] for p in body["image_gen_providers"]])
        res = self.client.post("/api/settings/ai/", json.dumps({**CFG, "ai_provider": body["ai_provider"], "ai_model": body["ai_model"], "ai_enabled": False}), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(image_generation_available())
        bad = self.client.post("/api/settings/ai/", json.dumps({**CFG, "image_gen_model": ""}), content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        url = "/api/settings/ai/image-generation/test/"
        with patch("core.views.settings.ai.ai_image_test_view.test_connection", return_value="fine"):
            self.assertEqual(self.client.post(url, json.dumps(CFG), content_type="application/json").json(), {"ok": True, "detail": "fine"})
        with patch("core.views.settings.ai.ai_image_test_view.test_connection", side_effect=ImageProviderError("down")):
            self.assertEqual(self.client.post(url, json.dumps(CFG), content_type="application/json").status_code, 502)
        self.client.force_login(self.user)
        self.assertNotEqual(self.client.post(url, json.dumps(CFG), content_type="application/json").status_code, 200)
