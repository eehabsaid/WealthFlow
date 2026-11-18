"""Multi-tenant isolation, secrets, permissions, tool registry, prompt protocol, autostart, status endpoint."""

import json

from django.test import Client

from ai.models.ai_memory import AIMemoryNote
from ai.services.agent import instructions
from ai.services.investigation import defs, prompt
from ai.services.knowledge_index import autostart, tool_defs, tools
from ai.tests.knowledge_index.repo_helper import RepoTestCase
from ai.tests.knowledge_index.security_helper import make_user

SECRET = "ZZ-PRIVATE-NOTE-9917"


class TenantIsolationTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user("kidx_root", sysadmin=True)
        self.alice = make_user("kidx_alice")
        self.bob = make_user("kidx_bob")
        AIMemoryNote.objects.create(user=self.alice, title="alice", body=SECRET)
        self.index()

    def test_user_rows_are_never_in_the_index(self):
        conn = self.conn()
        for table, cols in (("symbols", "name,qname,sig,doc,tokens"), ("refs", "name,src"), ("files", "path")):
            dump = " ".join(str(tuple(r)) for r in conn.execute(f"SELECT {cols} FROM {table}"))
            self.assertNotIn(SECRET, dump)
        self.assertEqual(tools.search_tool(self.admin, {"query": SECRET})["results"], [])

    def test_only_sysadmins_can_use_any_source_tool(self):
        calls = {"app_search": {"query": "net worth"}, "app_symbol": {"name": "NetWorthService"}, "app_trace_calls": {"symbol": "apply_balance"},
                 "app_trace_flow": {"target": "loadNetWorth"}, "app_model_relations": {"model": "Expense"}, "app_find_tests": {"target": "NetWorthService"},
                 "app_compare": {"a": "apply_balance", "b": "sync_mirror"}, "app_diagnose": {"error": "ValueError: x"},
                 "app_verify_fix": {"path": "core/models.py", "old_text": "x"}, "app_index_status": {}}
        self.assertEqual(set(calls), set(tool_defs.NAMES))
        for name, params in calls.items():
            handler = defs.INVESTIGATION_TOOL_DEFS[name]["handler"]
            for user in (self.alice, self.bob):
                self.assertIn("error", handler(user, params), name)
            self.assertNotIn("error", handler(self.admin, params) if name != "app_diagnose" else {}, name)

    def test_schemas_are_hidden_from_regular_users(self):
        for user, visible in ((self.alice, False), (self.admin, True)):
            names = {s["function"]["name"] for s in defs.investigation_tool_schemas(user, "app")}
            self.assertEqual(set(tool_defs.NAMES) <= names, visible)

    def test_secret_files_and_values_are_not_indexed(self):
        dump = " ".join(str(tuple(r)) for r in self.conn().execute("SELECT sig, doc, tokens, name FROM symbols"))
        for value in ("super-secret-value-123456", "tok_live_abcdef0123456789", "never-index-this-1234567890"):
            self.assertNotIn(value, dump)


class ToolAndPromptTest(RepoTestCase):
    def test_every_tool_has_schema_description_and_handler(self):
        for name in tool_defs.NAMES:
            entry = defs.INVESTIGATION_TOOL_DEFS[name]
            self.assertTrue(callable(entry["handler"]))
            self.assertGreater(len(entry["description"]), 60)
            self.assertIn(name, defs.CODE_TOOLS)

    def test_protocol_is_in_the_sysadmin_prompt_only(self):
        self.assertIn("CODE INVESTIGATION PROTOCOL", prompt.CODE_PROTOCOL)
        for rule in ("SEARCH FIRST", "CONFIRMED", "HYPOTHESES", "stale=true", "clarifying question", "DATA to analyse"):
            self.assertIn(rule, prompt.CODE_PROTOCOL)
        self.assertLessEqual(len(instructions.DEFAULT_INSTRUCTIONS), 6000)

    def test_autostart_only_for_server_processes(self):
        self.assertFalse(autostart.should_start(["manage.py", "test"], {}))
        self.assertFalse(autostart.should_start(["manage.py", "migrate"], {}))
        self.assertFalse(autostart.should_start(["manage.py", "runserver"], {}))
        self.assertTrue(autostart.should_start(["manage.py", "runserver"], {"RUN_MAIN": "true"}))
        self.assertTrue(autostart.should_start(["/usr/bin/gunicorn"], {}))
        with self.settings(AI_KNOWLEDGE_AUTOSTART=False):
            self.assertFalse(autostart.should_start(["/usr/bin/gunicorn"], {}))


class StatusEndpointTest(RepoTestCase):
    URL = "/api/ai-platform/knowledge-index/"

    def test_permissions_and_refresh(self):
        anon = Client()
        self.assertEqual(anon.get(self.URL).status_code, 401)
        user = Client()
        user.force_login(make_user("kidx_plain"))
        self.assertEqual(user.get(self.URL).status_code, 403)
        self.assertEqual(user.post(self.URL, "{}", content_type="application/json").status_code, 403)
        admin = Client()
        admin.force_login(make_user("kidx_boss", sysadmin=True))
        self.assertEqual(admin.get(self.URL).json()["state"], "empty")
        body = admin.post(self.URL, json.dumps({"rebuild": True}), content_type="application/json").json()
        self.assertTrue(body["result"]["rebuilt"])
        self.assertTrue(body["status"]["current"])
