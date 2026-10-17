"""The property maps' background is a per-user setting, and no code points at a tile server that needs an API key."""

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.models import AppSettings

User = get_user_model()


class MapTileSettingTest(TestCase):
    def test_a_plain_member_saves_and_reads_their_own_tile_server(self):
        member = User.objects.create_user(username="map_member", password="pass12345")
        other = User.objects.create_user(username="map_other", password="pass12345")
        self.client.force_login(member)
        url = "https://tiles.example.com/{z}/{x}/{y}.png"
        res = self.client.post("/api/settings/", data=json.dumps({"settings": {"map_tile_url": url, "map_tile_attribution": "© Example"}}),
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AppSettings.get("map_tile_url", user=member), url)
        self.assertIsNone(AppSettings.get("map_tile_url", user=None))   # never a platform-wide row
        self.assertEqual(self.client.get("/api/settings/").json()["settings"]["map_tile_url"], url)
        self.client.force_login(other)
        self.assertNotIn("map_tile_url", self.client.get("/api/settings/").json()["settings"])


class NoKeyedTileServerTest(SimpleTestCase):
    def test_no_script_uses_the_carto_basemaps_that_now_require_a_key(self):
        root = Path(settings.BASE_DIR) / "static" / "js"
        offenders = [str(p) for p in root.rglob("*.js") if "basemaps.cartocdn.com" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(offenders, [])
