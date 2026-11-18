"""Full indexing, incremental updates, deleted/renamed files, versioning, interrupted-run recovery."""

import os
from unittest import mock

from ai.services.knowledge_index import config, indexer, store
from ai.tests.knowledge_index.repo_helper import RepoTestCase


class FullIndexTest(RepoTestCase):
    def test_full_index_covers_every_source_kind(self):
        summary = self.index()
        self.assertTrue(summary["rebuilt"])
        conn = self.conn()
        paths = {r["path"] for r in conn.execute("SELECT path FROM files")}
        self.assertIn("core/models.py", paths)
        self.assertIn("static/js/net_worth/page.js", paths)
        self.assertIn("templates/index.html", paths)
        self.assertIn("static/css/app.css", paths)
        self.assertIn("static/i18n/en.json", paths)
        kinds = {r["kind"] for r in conn.execute("SELECT DISTINCT kind FROM symbols")}
        self.assertTrue({"class", "function", "method", "field", "route", "component", "css_rule", "i18n_key", "variable"} <= kinds, kinds)
        self.assertEqual(store.get_meta(conn, "state"), "ready")
        self.assertEqual(store.get_meta(conn, "version"), str(config.INDEX_VERSION))

    def test_unindexable_and_secret_files_are_skipped(self):
        self.index()
        paths = {r["path"] for r in self.conn().execute("SELECT path FROM files")}
        for bad in (".env", "db.sqlite3", "node_modules/pkg/index.js"):
            self.assertNotIn(bad, paths)


class IncrementalTest(RepoTestCase):
    def test_unchanged_files_are_not_reprocessed(self):
        self.index()
        second = self.index()
        self.assertEqual((second["parsed"], second["changed"], second["added"]), (0, 0, 0))

    def test_touching_a_file_without_changing_content_does_not_reparse(self):
        self.index()
        target = self.root / "core/models.py"
        os.utime(target, ns=(target.stat().st_atime_ns, target.stat().st_mtime_ns + 5_000_000_000))
        self.assertEqual(self.index()["parsed"], 0)

    def test_changed_file_is_reparsed_and_new_symbol_is_found(self):
        self.index()
        self.write("core/services/net_worth.py", (self.root / "core/services/net_worth.py").read_text() + "\n\ndef liabilities_total(owner):\n    return 0\n")
        summary = self.index()
        self.assertEqual((summary["changed"], summary["parsed"]), (1, 1))
        row = self.conn().execute("SELECT line FROM symbols WHERE name='liabilities_total'").fetchone()
        self.assertIsNotNone(row)

    def test_new_file_is_added(self):
        self.index()
        self.write("core/services/extra.py", "def extra_fn():\n    return 1\n")
        self.assertEqual(self.index()["added"], 1)


class DeletedAndRenamedTest(RepoTestCase):
    def test_deleted_file_loses_all_rows(self):
        self.index()
        (self.root / "core/services/mirror.py").unlink()
        self.assertEqual(self.index()["deleted"], 1)
        conn = self.conn()
        for table in ("symbols", "refs", "files"):
            self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE path='core/services/mirror.py'").fetchone()[0], 0)

    def test_rename_moves_rows_without_reparsing(self):
        self.index()
        (self.root / "core/services/mirror.py").rename(self.root / "core/services/mirror_engine.py")
        summary = self.index()
        self.assertEqual((summary["renamed"], summary["parsed"], summary["deleted"], summary["added"]), (1, 0, 0, 0))
        conn = self.conn()
        row = conn.execute("SELECT path FROM symbols WHERE name='sync_mirror'").fetchone()
        self.assertEqual(row["path"], "core/services/mirror_engine.py")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM symbols WHERE path='core/services/mirror.py'").fetchone()[0], 0)


class VersionAndRecoveryTest(RepoTestCase):
    def test_version_change_triggers_a_rebuild(self):
        self.index()
        with mock.patch.object(config, "INDEX_VERSION", config.INDEX_VERSION + 1):
            self.assertTrue(self.index()["rebuilt"])

    def test_explicit_rebuild(self):
        self.index()
        self.assertTrue(self.index(full=True)["rebuilt"])

    def test_interrupted_indexing_recovers_to_the_same_result(self):
        real = store.write_file
        calls = {"n": 0}

        def crash(conn, rec, symbols, refs):
            calls["n"] += 1
            if calls["n"] == 4:
                raise RuntimeError("power cut")
            return real(conn, rec, symbols, refs)

        with mock.patch.object(store, "write_file", crash), self.assertRaises(RuntimeError):
            self.index()
        conn = self.conn()
        self.assertEqual(store.get_meta(conn, "state"), "building")
        recovered = self.index()
        self.assertTrue(recovered["recovered"])
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("files", "symbols", "refs")}
        fresh = self.tmp / "fresh.sqlite3"
        with self.settings(AI_KNOWLEDGE_INDEX_PATH=str(fresh)):
            indexer.refresh()
            other = store.connect()
            expected = {t: other.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("files", "symbols", "refs")}
            other.close()
        self.assertEqual(counts, expected)
        self.assertEqual(store.get_meta(conn, "state"), "ready")

    def test_damaged_file_record_is_detected_and_repaired(self):
        self.index()
        conn = self.conn()
        conn.execute("DELETE FROM symbols WHERE path='core/models.py' AND kind='field'")
        conn.commit()
        self.assertGreaterEqual(indexer.status(conn)["stale_files"], 1)
        self.assertFalse(indexer.status(conn)["current"])
        self.assertGreaterEqual(self.index()["invalid_repaired"], 1)
        self.assertTrue(indexer.status(conn)["current"])
        self.assertGreater(conn.execute("SELECT COUNT(*) FROM symbols WHERE path='core/models.py' AND kind='field'").fetchone()[0], 0)
