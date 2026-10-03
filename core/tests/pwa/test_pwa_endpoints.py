import json
import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.auth import get_user_model
from django.test import TestCase
from PIL import Image


def _static_file(url):
    return finders.find(url.replace(settings.STATIC_URL, "", 1))


class PwaEndpointTests(TestCase):
    def test_manifest_is_public_and_valid(self):
        response = self.client.get("/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        data = json.loads(response.content)
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["start_url"], "/")
        self.assertEqual(data["scope"], "/")
        self.assertTrue(data["name"] and data["short_name"])

    def test_manifest_icons_exist_with_declared_size(self):
        data = json.loads(self.client.get("/manifest.webmanifest").content)
        sizes = {icon["sizes"] for icon in data["icons"]}
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)
        self.assertIn("maskable", {icon["purpose"] for icon in data["icons"]})
        for icon in data["icons"]:
            path = _static_file(icon["src"])
            self.assertTrue(path and os.path.exists(path), icon["src"])
            width, height = Image.open(path).size
            self.assertEqual(f"{width}x{height}", icon["sizes"])

    def test_service_worker_is_public_root_scoped_and_not_cached(self):
        response = self.client.get("/service-worker.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertEqual(response["Cache-Control"], "no-cache")

    def test_service_worker_never_caches_api_or_non_get(self):
        body = self.client.get("/service-worker.js").content.decode()
        self.assertIn('request.method !== "GET"', body)
        self.assertIn('url.pathname.startsWith("/static/")', body)
        self.assertNotIn("/api/", body)

    def test_service_worker_precache_list_resolves_to_real_files(self):
        body = self.client.get("/service-worker.js").content.decode()
        start = body.index("const PRECACHE_URLS = ") + len("const PRECACHE_URLS = ")
        urls = json.loads(body[start:body.index(";", start)])
        self.assertIn("/offline/", urls)
        for url in urls:
            if url.startswith(settings.STATIC_URL):
                self.assertTrue(_static_file(url), url)
            else:
                self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_offline_page_is_public(self):
        response = self.client.get("/offline/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-i18n="pwa_offline_title"')

    def test_post_to_pwa_routes_rejected(self):
        for url in ("/manifest.webmanifest", "/service-worker.js", "/offline/"):
            self.assertEqual(self.client.post(url).status_code, 405)

    def test_shell_and_login_link_the_manifest_and_register_worker(self):
        user = get_user_model().objects.create_user("pwa_user", "pwa@example.com", "pw-12345-x")
        self.client.force_login(user)
        for url in ("/", "/accounts/login/"):
            html = self.client.get(url, follow=True).content.decode()
            self.assertIn('rel="manifest"', html, url)
            self.assertIn("js/pwa/register.js", html, url)
            self.assertIn("apple-touch-icon", html, url)

    def test_anonymous_login_page_links_the_manifest(self):
        html = self.client.get("/accounts/login/").content.decode()
        self.assertIn('rel="manifest"', html)
        self.assertIn("js/pwa/register.js", html)

    def test_offline_i18n_keys_exist_in_every_language(self):
        for lang in ("en", "ar", "fr", "de"):
            path = finders.find(f"i18n/{lang}.json")
            with open(path, encoding="utf-8") as fh:
                messages = json.load(fh)
            for key in ("pwa_offline_title", "pwa_offline_message", "pwa_offline_retry"):
                self.assertTrue(messages.get(key), f"{lang}:{key}")
