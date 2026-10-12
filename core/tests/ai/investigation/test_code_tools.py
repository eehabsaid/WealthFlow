"""Path safety, secret redaction and the sysadmin-only source-code tools."""

from __future__ import annotations

import os
import tempfile

from django.test import SimpleTestCase, TestCase

from core.models import AppSettings
from core.services.ai.investigation import code_tools as ct
from core.services.ai.investigation import paths

from .support import make_user


class PathSafetyTest(SimpleTestCase):
    def test_blocked_and_escaping_paths(self):
        for bad in ("../etc/passwd", "core/../../x", "node_modules/eslint", ".git/config", "db.sqlite3", ".env", "backups"):
            with self.assertRaises(paths.PathError, msg=bad):
                paths.resolve(bad)

    def test_absolute_path_is_treated_as_relative_and_cannot_escape(self):
        with self.assertRaises(paths.PathError):
            paths.resolve("/etc/passwd")

    def test_symlink_cannot_escape_the_project(self):
        outside = tempfile.mkdtemp()
        open(os.path.join(outside, "secret.txt"), "w").write("top secret")
        link = paths.BASE / "_zz_link_test"
        os.symlink(outside, link)
        try:
            with self.assertRaises(paths.PathError):
                paths.resolve("_zz_link_test/secret.txt")
        finally:
            link.unlink()

    def test_listing_excludes_vendor_secrets_and_binaries(self):
        files = [p for p, _ in paths.iter_files()]
        self.assertTrue(files)
        self.assertFalse([p for p in files if p.startswith(("node_modules/", ".git/")) or p.endswith((".sqlite3", ".pyc", ".png"))])

    def test_file_cache_builds_even_when_monotonic_clock_is_near_zero(self):
        from unittest.mock import patch

        saved = dict(paths._CACHE)
        try:
            paths._CACHE.update(at=None, files=[])
            with patch("core.services.ai.investigation.paths.time.monotonic", return_value=5.0):   # just after boot
                self.assertTrue(paths.iter_files())
        finally:
            paths._CACHE.update(saved)

    def test_redaction(self):
        text = 'SECRET_KEY = "django-insecure-abc123def456"\npassword = \'hunter2\'\nname = "visible"\n' \
               'k = "0123456789abcdef0123456789abcdef0123456789abcdef"\nx = os.environ.get("TOKEN", "")'
        out = paths.redact(text)
        for leak in ("django-insecure", "hunter2", "0123456789abcdef0123"):
            self.assertNotIn(leak, out)
        self.assertIn('name = "visible"', out)
        self.assertIn('os.environ.get("TOKEN", "")', out)


class CodeToolsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("code_admin", sysadmin=True)
        cls.customer = make_user("code_customer")

    def test_customer_is_denied_by_every_code_tool(self):
        for fn, args in ((ct.list_dir, {}), (ct.find_files, {"pattern": "x"}), (ct.grep, {"pattern": "x"}),
                         (ct.find_definition, {"symbol": "ExpenseService"}), (ct.read_file, {"path": "manage.py"})):
            res = fn(self.customer, args)
            self.assertIn("system administrator", res.get("error", ""), fn.__name__)

    def test_the_gate_is_the_app_sysadmin_flag_not_djangos_superuser(self):
        su = make_user("code_django_su", django_superuser=True)        # Django superuser, NOT an app sysadmin
        self.assertIn("error", ct.read_file(su, {"path": "manage.py"}))
        self.assertFalse(ct.code_access_allowed(su))
        self.assertTrue(ct.code_access_allowed(self.admin))              # app sysadmin, not a Django superuser
        self.assertFalse(ct.code_access_allowed(None))

    def test_switch_off_denies_even_the_sysadmin(self):
        AppSettings.set("ai_code_access", "false")
        self.assertIn("error", ct.read_file(self.admin, {"path": "manage.py"}))
        AppSettings.set("ai_code_access", "true")
        self.assertNotIn("error", ct.read_file(self.admin, {"path": "manage.py"}))

    def test_find_definition_and_grep_and_find_files(self):
        d = ct.find_definition(self.admin, {"symbol": "ExpenseService"})
        self.assertEqual(d["definitions"][0]["file"], "core/services/expenses/expense_service.py")
        g = ct.grep(self.admin, {"pattern": "_sync_asset_renovations", "path": "core/services"})
        self.assertGreaterEqual(g["total_matches"], 2)
        self.assertTrue(any("def _sync_asset_renovations" in m["text"] for m in g["matches"]))
        many = ct.grep(self.admin, {"pattern": "^def ", "path": "core/services", "max_results": 3})
        self.assertEqual(len(many["matches"]), 3)
        self.assertIn("more matches", many["note"])
        f = ct.find_files(self.admin, {"pattern": "*expense_mirror*"})
        self.assertIn("core/services/shared/expense_mirror_engine.py", f["files"])
        self.assertIn("core/services/shared/expense_mirror_engine.py", ct.find_files(self.admin, {"pattern": "mirror_engine"})["files"])

    def test_grep_falls_back_to_literal_on_bad_regex_and_hints_on_no_match(self):
        self.assertNotIn("error", ct.grep(self.admin, {"pattern": "def ("}))
        needle = "zzqqxx_" + "nothing_like_this_9981"   # split so this very file does not contain the literal
        none = ct.grep(self.admin, {"pattern": needle})
        self.assertEqual(none["total_matches"], 0)
        self.assertIn("no match", none["note"])

    def test_read_file_numbers_lines_pages_and_blocks_secrets(self):
        r = ct.read_file(self.admin, {"path": "manage.py", "start_line": 1, "end_line": 3})
        self.assertTrue(r["content"].startswith("1: "))
        self.assertEqual(r["end_line"], 3)
        big = ct.read_file(self.admin, {"path": "core/views/__init__.py", "start_line": 1, "end_line": 5000})
        self.assertLessEqual(big["end_line"] - big["start_line"] + 1, ct.MAX_READ_LINES)
        for blocked in ("db.sqlite3", ".env", "../x", "node_modules/eslint/package.json"):
            self.assertIn("error", ct.read_file(self.admin, {"path": blocked}), blocked)
        self.assertIn("directory", ct.read_file(self.admin, {"path": "core"})["error"])

    def test_list_dir_hides_vendor_dirs(self):
        root = ct.list_dir(self.admin, {})
        self.assertIn("core/", root["entries"])
        self.assertNotIn("node_modules/", root["entries"])
        self.assertFalse([e for e in root["entries"] if e.startswith((".git/", "db.sqlite3"))])

    def test_bad_input_returns_errors_not_exceptions(self):
        self.assertIn("error", ct.grep(self.admin, {"pattern": "  "}))
        self.assertIn("error", ct.find_files(self.admin, {}))
        self.assertIn("error", ct.find_definition(self.admin, {"symbol": "a b; rm -rf"}))
        self.assertIn("error", ct.list_dir(self.admin, {"path": "no/such/dir"}))
