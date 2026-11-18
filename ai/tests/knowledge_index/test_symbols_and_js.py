"""Python / JavaScript symbol retrieval, WealthFlow script-global cross-file references, dependency tracing, models, i18n."""

import json
from unittest import skipUnless

from ai.services.knowledge_index import flow, indexer, relations
from ai.services.knowledge_index.parsers import js_acorn, js_scan
from ai.tests.knowledge_index.repo_helper import FILES, RepoTestCase


class PythonSymbolsTest(RepoTestCase):
    def test_classes_methods_functions_and_docstrings(self):
        self.index()
        conn = self.conn()
        cls = relations.definitions(conn, "NetWorthService", ("class",))[0]
        self.assertEqual((cls["path"], cls["line"]), ("core/services/net_worth.py", 4))
        self.assertEqual(relations.definitions(conn, "NetWorthService.total", ("method",))[0]["line"], 7)
        self.assertIn("sum of all account balances", conn.execute("SELECT doc FROM symbols WHERE name='NetWorthService'").fetchone()["doc"])
        self.assertTrue(relations.definitions(conn, "apply_balance", ("function",)))

    def test_routes_resolve_to_views(self):
        self.index()
        conn = self.conn()
        route = conn.execute("SELECT * FROM symbols WHERE kind='route' AND name='api/net-worth/'").fetchone()
        self.assertEqual(route["path"], "core/urls.py")
        view = conn.execute("SELECT name FROM refs WHERE kind='route_view' AND src='api/net-worth/'").fetchone()
        self.assertEqual(view["name"], "NetWorthView")

    def test_model_relations_with_owner_scoping(self):
        self.index()
        info = relations.model_relations(self.conn(), "Expense")
        self.assertTrue(info["found"])
        self.assertTrue(info["multi_tenant_owner_field"])
        self.assertIn("Account", [f["to"] for f in info["foreign_keys_out"]])
        account = relations.model_relations(self.conn(), "Account")
        self.assertIn("Expense.account", [r["model_field"] for r in account["referenced_by"]])
        self.assertFalse(relations.model_relations(self.conn(), "GhostModel")["found"])


class JavaScriptGlobalsTest(RepoTestCase):
    def _check_globals(self):
        self.index()
        conn = self.conn()
        names = {r["name"]: r for r in conn.execute("SELECT name, path, kind FROM symbols WHERE path LIKE 'static/js/%'")}
        for name in ("formatMoney", "WF_CURRENCY", "loadNetWorth", "renderNetWorth", "refreshNetWorth", "showNetWorthAgain"):
            self.assertIn(name, names)
        self.assertNotIn("fake", names)                       # a function inside a string literal is not a definition
        self.assertEqual(names["formatMoney"]["path"], "static/js/utils/format.js")
        users = {(c["path"], c["in"]) for c in relations.callers(conn, "formatMoney")}
        self.assertIn(("static/js/net_worth/page.js", "renderNetWorth"), users)       # cross-file global use
        self.assertIn("static/js/net_worth/page.js", {c["path"] for c in relations.callers(conn, "WF_CURRENCY")})
        render_users = {c["path"] for c in relations.callers(conn, "renderNetWorth")}
        self.assertIn("static/js/net_worth/other.js", render_users)
        self.assertIn("templates/index.html", {c["path"] for c in relations.callers(conn, "refreshNetWorth")})   # inline onclick handler

    def test_script_globals_with_the_active_engine(self):
        self._check_globals()

    def test_pure_python_scanner_engine(self):
        with self.settings(AI_KNOWLEDGE_JS_ENGINE="python"):
            self._check_globals()
            self.assertEqual({r["parser"] for r in self.conn().execute("SELECT parser FROM files WHERE path LIKE '%.js'")}, {"js-scan"})

    @skipUnless(js_acorn.available(), "node + acorn not installed")
    def test_acorn_engine_matches_the_scanner(self):
        with self.settings(AI_KNOWLEDGE_JS_ENGINE="acorn"):
            self._check_globals()
            self.assertEqual({r["parser"] for r in self.conn().execute("SELECT parser FROM files WHERE path LIKE '%.js'")}, {"acorn"})
        for rel in [p for p in FILES if p.endswith(".js") and p.startswith("static")]:
            text = FILES[rel]
            scan = {s["name"] for s in js_scan.parse(text)[0] if s.get("scope") == "global"}
            acorn = {s["name"] for s in js_acorn.parse_many([(rel, self.root / rel)])[rel][0] if s["scope"] == "global"}
            self.assertEqual(scan, acorn, rel)

    def test_endpoint_literals_are_recorded(self):
        self.index()
        row = self.conn().execute("SELECT src, name FROM refs WHERE kind='endpoint'").fetchone()
        self.assertEqual((row["src"], row["name"]), ("loadNetWorth", "api/net-worth/"))


class DependencyTraceTest(RepoTestCase):
    def test_callers_and_callees_across_files(self):
        self.index()
        conn = self.conn()
        up = relations.trace_calls(conn, "apply_balance", "up", 2)
        self.assertIn("sync_mirror", {c["in"] for lvl in up["callers"] for c in lvl})
        down = relations.trace_calls(conn, "NetWorthView", "down", 2)
        names = {c["name"] for lvl in down["callees"] for c in lvl}
        self.assertIn("NetWorthService", names)
        self.assertFalse(relations.trace_calls(conn, "ghost_fn")["found"])

    def test_feature_trace_screen_to_backend(self):
        self.index()
        result = flow.trace_flow(self.conn(), "loadNetWorth")
        layers = {layer["layer"]: layer for layer in result["layers"]}
        self.assertIn("api/net-worth/", {e["endpoint"] for e in layers["API calls found in that JS"]["items"]})
        route = layers["route api/net-worth/"]
        self.assertEqual(route["view"][0]["symbol"], "NetWorthView")
        self.assertIn("NetWorthService", {s["symbol"] for s in route["service"]})
        self.assertIn("Account", {m["symbol"] for m in route["model"]} | {"Account"})
        self.assertEqual(route["frontend_callers"][0]["path"], "static/js/net_worth/page.js")

    def test_tests_for_a_symbol_and_for_a_file(self):
        self.index()
        conn = self.conn()
        by_symbol = relations.find_tests(conn, "NetWorthService")
        self.assertEqual([t["path"] for t in by_symbol["tests"]], ["core/tests/test_net_worth.py"])
        self.assertTrue(relations.find_tests(conn, "core/services/net_worth.py")["covered"])
        self.assertFalse(relations.find_tests(conn, "GhostService")["covered"])


class TranslationIndexTest(RepoTestCase):
    def test_keys_in_all_four_locales_and_gaps(self):
        self.index()
        conn = self.conn()
        key = conn.execute("SELECT doc, line FROM symbols WHERE kind='i18n_key' AND name='nw_title'").fetchone()
        self.assertIn("Net worth", key["doc"])
        self.assertEqual({r["parent"] for r in conn.execute("SELECT DISTINCT parent FROM symbols WHERE kind='i18n_value'")}, {"ar", "fr", "de"})
        gaps = relations.i18n_gaps(conn)
        self.assertEqual(gaps["de"]["examples"], ["nw_hint"])
        self.assertEqual(gaps["fr"]["missing"], 0)
        self.assertEqual(indexer.status(conn)["translations_missing"]["de"], 1)
        refs = conn.execute("SELECT name FROM refs WHERE kind='i18n' AND path='templates/index.html'").fetchall()
        self.assertEqual([r["name"] for r in refs], ["nw_title"])
        self.assertEqual(json.loads(FILES["static/i18n/en.json"])["nw_title"], "Net worth")
