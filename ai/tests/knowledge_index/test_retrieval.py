"""Hybrid relevance, exact source/line references, stale-index detection, missing evidence, diagnose and verify."""

from unittest import mock

from ai.services.knowledge_index import diagnose, evidence, indexer, relations, search, session, vectors, verify
from ai.tests.knowledge_index.repo_helper import FILES, RepoTestCase


class HybridSearchTest(RepoTestCase):
    def test_keyword_search_ranks_the_real_implementation_first(self):
        self.index()
        res = search.search(self.conn(), "how is net worth calculated")
        self.assertEqual(res["results"][0]["path"], "core/services/net_worth.py")
        self.assertEqual(res["mode"], "keyword")
        self.assertTrue(res["note"])

    def test_exact_identifier_beats_words(self):
        self.index()
        res = search.search(self.conn(), "apply_balance")
        self.assertEqual((res["results"][0]["symbol"], res["results"][0]["kind"]), ("apply_balance", "function"))

    def test_path_and_kind_filters(self):
        self.index()
        res = search.search(self.conn(), "net worth", path="static/js", kinds=("function",))
        self.assertTrue(res["results"])
        self.assertTrue(all(r["path"].startswith("static/js") and r["kind"] == "function" for r in res["results"]))

    def test_context_paths_boost_nearby_code(self):
        self.index()
        plain = search.search(self.conn(), "balance")["results"]
        boosted = search.search(self.conn(), "balance", context_paths=("core/models.py",))["results"]
        self.assertGreaterEqual(max(r["score"] for r in boosted if r["path"] == "core/models.py"),
                                max(r["score"] for r in plain if r["path"] == "core/models.py"))

    def test_semantic_layer_finds_code_with_no_shared_words(self):
        self.index()
        conn = self.conn()

        def fake(text):
            return [1.0, 0.0] if "NetWorthService" in text or "wealth" in text else [0.0, 1.0]

        with mock.patch.object(vectors.embeddings, "_embed", side_effect=fake), mock.patch.object(vectors.embeddings, "_embed_query", side_effect=fake):
            done = vectors.embed_pending(conn, 500)
            self.assertTrue(done["available"])
            res = search.search(conn, "wealth")
        self.assertEqual(res["mode"], "hybrid")
        self.assertIn("NetWorthService", [r["symbol"] for r in res["results"][:3]])

    def test_vectors_survive_a_reparse_of_unchanged_symbols(self):
        self.index()
        conn = self.conn()
        with mock.patch.object(vectors.embeddings, "_embed", return_value=[1.0, 0.0]):
            vectors.embed_pending(conn, 500)
        before = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        self.write("core/services/net_worth.py", FILES["core/services/net_worth.py"] + "\n# comment only\n")
        self.index()
        self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0], before - 1)

    def test_search_works_without_embeddings(self):
        self.index()
        with mock.patch.object(vectors.embeddings, "_embed_query", return_value=None):
            self.assertEqual(search.search(self.conn(), "net worth")["mode"], "keyword")


class ExactEvidenceTest(RepoTestCase):
    def test_line_range_and_content_match_the_file_exactly(self):
        self.index()
        item = search.search(self.conn(), "NetWorthService.total")["results"][0]
        lines = (self.root / item["path"]).read_text().splitlines()
        self.assertFalse(item["stale"])
        for numbered in item["content"].splitlines():
            no, text = numbered.split(": ", 1)
            self.assertEqual(lines[int(no) - 1], text)
        self.assertEqual(item["line_start"], 7)
        self.assertEqual(item["line_end"], 9)
        self.assertIn("Account.objects.filter(owner=owner)", item["content"])
        self.assertIn("used_by", item["relations"])

    def test_credentials_in_source_are_masked_in_content_and_in_the_index(self):
        self.write("core/services/leaky.py", 'def connect():\n    api_key = "sk-live-9999999999abcdef"\n    return api_key\n')
        self.index()
        item = search.search(self.conn(), "connect", path="core/services/leaky.py")["results"][0]
        self.assertNotIn("sk-live-9999999999abcdef", item["content"])
        dump = " ".join(str(tuple(r)) for r in self.conn().execute("SELECT sig, doc, tokens FROM symbols WHERE path='core/services/leaky.py'"))
        self.assertNotIn("sk-live-9999999999abcdef", dump)


class StaleIndexTest(RepoTestCase):
    def test_changed_file_is_never_shown_as_current(self):
        self.index()
        conn = self.conn()
        row = relations.definitions(conn, "NetWorthService", ("class",))[0]
        self.write("core/services/net_worth.py", "# rewritten\n" + FILES["core/services/net_worth.py"].replace("sum(", "max("))
        item = evidence.build(conn, row)
        self.assertTrue(item["stale"])
        self.assertIsNone(item["content"])
        self.assertIn("NOT current source", item["warning"])
        status = indexer.status(conn)
        self.assertFalse(status["current"])
        self.assertIn("core/services/net_worth.py", status["pending"]["changed"])

    def test_queries_refresh_automatically_and_return_current_lines(self):
        from ai.services.knowledge_index import tools

        self.index()
        self.write("core/services/net_worth.py", "# one extra line\n" + FILES["core/services/net_worth.py"])
        session.reset_throttle()
        user = _sysadmin()
        out = tools.symbol_tool(user, {"name": "NetWorthService"})
        self.assertEqual(out["index_refreshed"]["changed"], 1)
        self.assertEqual(out["definitions"][0]["line_start"], 5)
        self.assertFalse(out["definitions"][0]["stale"])

    def test_a_failed_refresh_is_reported_not_hidden(self):
        from ai.services.knowledge_index import tools

        self.index()
        self.write("core/services/net_worth.py", FILES["core/services/net_worth.py"] + "\n# x\n")
        session.reset_throttle()
        with mock.patch.object(indexer, "refresh", side_effect=RuntimeError("disk full")):
            out = tools.symbol_tool(_sysadmin(), {"name": "NetWorthService"})
        self.assertIn("index_warning", out)
        self.assertTrue(out["definitions"][0]["stale"])


class MissingEvidenceTest(RepoTestCase):
    def test_nothing_found_is_stated_not_invented(self):
        self.index()
        res = search.search(self.conn(), "zzzqqqunicorn_ledger")
        self.assertEqual(res["results"], [])
        self.assertIn("Do NOT assume", res["note"])

    def test_unknown_symbol_and_unknown_dependency(self):
        from ai.services.knowledge_index import tools

        self.index()
        user = _sysadmin()
        self.assertFalse(tools.symbol_tool(user, {"name": "GhostService"})["found"])
        self.assertFalse(tools.trace_calls_tool(user, {"symbol": "ghost_fn"})["found"])
        self.assertEqual(tools.search_tool(user, {})["error"][:9], "query is ")

    def test_verify_fix_rejects_invented_symbols_and_wrong_text(self):
        self.index()
        conn = self.conn()
        bad = verify.verify_fix(conn, "core/services/mirror.py", "no such text", "x", ["invented_helper"])
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertTrue(all(c["status"] == "FAIL" for c in bad["checks"] if c["check"].startswith(("old text", "symbol exists"))))


class DiagnoseAndVerifyTest(RepoTestCase):
    TRACE = 'Traceback (most recent call last):\n  File "/srv/app/core/services/mirror.py", line 7, in apply_balance\n' \
            "    account.balance = account.balance - amount\nAttributeError: 'NoneType' object has no attribute 'balance'\n"

    def test_traceback_is_mapped_to_real_source(self):
        self.index()
        out = diagnose.diagnose(self.conn(), self.TRACE)
        frame = out["confirmed_frames"][0]
        self.assertEqual((frame["path"], frame["failing_line"], frame["symbol"]), ("core/services/mirror.py", 7, "apply_balance"))
        self.assertIn("7:     account.balance = account.balance - amount", frame["content"])
        self.assertTrue(all(h["status"].startswith("HYPOTHESIS") for h in out["hypotheses"]))
        self.assertTrue(out["hypotheses"])

    def test_js_console_error_is_mapped_too(self):
        self.index()
        out = diagnose.diagnose(self.conn(), "TypeError: Cannot read properties of undefined (reading 'total')\n    at renderNetWorth (http://localhost:8000/static/js/net_worth/page.js:7:30)")
        self.assertEqual(out["confirmed_frames"][0]["path"], "static/js/net_worth/page.js")

    def test_verify_fix_passes_a_safe_change_and_flags_a_syntax_error(self):
        self.index()
        conn = self.conn()
        old = "    account.balance = account.balance - amount\n"
        good = verify.verify_fix(conn, "core/services/mirror.py", old, "    account.balance -= amount\n", ["apply_balance"])
        self.assertEqual(good["verdict"], "PASS", good)
        self.assertEqual(good["impact"]["changed_symbol"], "apply_balance")
        broken = verify.verify_fix(conn, "core/services/mirror.py", old, "    account.balance = (\n")
        self.assertEqual(broken["verdict"], "FAIL")
        js = verify.verify_fix(conn, "static/js/utils/format.js", "return Number(value).toFixed(2);", "return (Number(value).toFixed(2);")
        self.assertEqual(js["verdict"], "FAIL")


def _sysadmin():
    from ai.tests.knowledge_index.security_helper import make_user

    return make_user("kidx_admin", sysadmin=True)
