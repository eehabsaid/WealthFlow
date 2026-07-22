import os
import json
import unittest

import struct
from doc_engine.services.inventory_provider import InventoryProvider
from doc_engine.services.navigation_planner import NavigationPlanner, sanitize_filename, safe_filename
from doc_engine.services.manifest_service import ManifestService
from doc_engine.config import LATEST_SCREENSHOTS_DIR, RUNTIME_DIR, MANIFEST_FILE, STATUS_FILE


def get_png_dimensions(file_path):
    """Parses PNG header to extract (width, height) without external image dependencies."""
    with open(file_path, 'rb') as f:
        data = f.read(25)
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return None
        width, height = struct.unpack('>II', data[16:24])
        return width, height


class TestPlaywrightMigrationServices(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Financial Advisor"), "financial_advisor")
        self.assertEqual(sanitize_filename("Fixed-Assets / Real Estate"), "fixed_assets_real_estate")
        self.assertEqual(sanitize_filename(""), "")

    def test_safe_filename_arabic_fallback(self):
        # Arabic string sanitizes to empty string -> should fallback to clean fallback_id
        arabic_title = "مستشار مالي"
        result = safe_filename(arabic_title, "tab-financial-advisor-tab")
        self.assertEqual(result, "tab_financial_advisor")

    def test_inventory_provider(self):
        provider = InventoryProvider()
        inventory = provider.get_page_inventory()
        self.assertIsInstance(inventory, list)
        self.assertGreater(len(inventory), 0)

        device_inventory = provider.get_device_inventory()
        self.assertIsInstance(device_inventory, dict)

    def test_navigation_planner(self):
        planner = NavigationPlanner("http://127.0.0.1:8001")
        self.assertEqual(planner.get_full_url("dashboard"), "http://127.0.0.1:8001/#dashboard")
        self.assertEqual(planner.get_full_url("/accounts/login/"), "http://127.0.0.1:8001/accounts/login/")
        self.assertTrue(planner.is_chart_route("dashboard"))
        self.assertFalse(planner.is_chart_route("settings"))

    def test_manifest_service(self):
        ms = ManifestService(language='en', theme='dark', device='desktop')
        ctx = {"page_id": "dash", "page_title": "Dashboard", "route": "dashboard"}
        ms.record_screenshot(ctx, "dashboard_main")
        self.assertEqual(ms.screenshots_count, 1)
        self.assertEqual(len(ms.manifest["pages"]), 1)
        self.assertEqual(ms.manifest["pages"][0]["filename"], "dashboard_main.png")


class TestPlaywrightMigrationComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screenshots_dir = LATEST_SCREENSHOTS_DIR
        cls.runtime_dir = RUNTIME_DIR

    def test_runtime_files_exist(self):
        """Verifies status.json can be loaded and has valid structure."""
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
            self.assertIn("status", status_data)
            self.assertIn("screenshots_count", status_data)

    def test_manifest_valid_json(self):
        """Verifies manifest.json if present conforms to expected schema."""
        if os.path.exists(MANIFEST_FILE):
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            self.assertIn("schema_version", manifest_data)
            self.assertIn("pages", manifest_data)
            self.assertIsInstance(manifest_data["pages"], list)


if __name__ == "__main__":
    unittest.main()
