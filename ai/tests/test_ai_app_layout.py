"""The AI code lives in app `ai`: labels, table names, routes, migration rules, ContentType relabel."""
import importlib.util

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase
from django.urls import resolve

from ai.migrations_support import MODELS, relabel_backward, relabel_forward

NAMES = ["AIKnowledgeEntry", "AIPromptCategory", "AIConversation", "AIMemoryNote", "AIMessage",
         "AIChatBlock", "AIAttachment", "AIPrompt", "AIAnswerFeedback"]


class _Editor:
    connection = connection


class AppLayoutTests(SimpleTestCase):
    def test_models_live_in_ai_and_keep_core_table_names(self):
        for name in NAMES:
            model = apps.get_model("ai", name)
            self.assertEqual(model._meta.db_table, "core_" + name.lower())
            with self.assertRaises(LookupError):
                apps.get_model("core", name)

    def test_training_app_keeps_its_label(self):
        cfg = apps.get_app_config("ai_training")
        self.assertEqual(cfg.name, "ai.training")
        self.assertEqual(apps.get_model("ai_training", "AgentTrace")._meta.db_table, "ai_training_agenttrace")

    def test_old_import_paths_are_gone(self):
        for old in ("core.services.ai", "core.models.ai_message", "core.views.ai_chat", "ai_training"):
            spec = importlib.util.find_spec(old)
            self.assertTrue(spec is None or spec.origin is None, old)  # a bare leftover folder is no module

    def test_ai_routes_resolve_to_ai_views(self):
        for url in ("/api/financial-advisor/ai/chat/", "/api/settings/ai/", "/api/ai-platform/knowledge/",
                    "/api/financial-advisor/ai/speech/capabilities/"):
            self.assertTrue(resolve(url).func.__module__.startswith("ai."), url)

    def test_ai_first_migration_never_depends_on_core(self):
        graph = MigrationLoader(None, load=True).graph
        parents = {app for app, _ in graph.node_map[("ai", "0001_initial")].parents}
        self.assertNotIn("core", parents)


class ContentTypeRelabelTests(TestCase):
    def test_relabel_keeps_original_id_and_drops_empty_duplicate(self):
        original = ContentType.objects.get(app_label="ai", model="aimessage")
        dup = ContentType.objects.create(app_label="core", model="aimessage")
        self.assertGreater(dup.id, original.id)
        relabel_forward(apps, _Editor)
        rows = ContentType.objects.filter(model="aimessage")
        self.assertEqual([(r.id, r.app_label) for r in rows], [(original.id, "ai")])

    def test_relabel_roundtrip_moves_every_model_without_new_ids(self):
        before = {m: ContentType.objects.get(app_label="ai", model=m).id for m in MODELS}
        relabel_backward(apps, _Editor)
        self.assertEqual({m: ContentType.objects.get(app_label="core", model=m).id for m in MODELS}, before)
        relabel_forward(apps, _Editor)
        self.assertEqual({m: ContentType.objects.get(app_label="ai", model=m).id for m in MODELS}, before)
