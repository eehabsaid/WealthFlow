"""The query engine's cost estimate uses the current machine's throughput, and the settings migration only replaces old defaults."""

from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.query_engine.llm_slots import estimate_seconds

migration = import_module("core.migrations.0035_refresh_ai_throughput_settings")


class ThroughputDefaultsTest(TestCase):
    def test_estimate_uses_the_current_machine_defaults(self):
        AppSettings.objects.filter(key__in=("ai_prompt_tps", "ai_decode_tps")).delete()
        self.assertAlmostEqual(estimate_seconds(300, 40), 300 / 700 + 40 / 30, places=3)

    def test_migration_replaces_only_the_old_defaults(self):
        AppSettings.set("ai_prompt_tps", "36.9")
        AppSettings.set("ai_decode_tps", "42")          # typed by the owner: must stay
        migration.forwards(django_apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "700")
        self.assertEqual(AppSettings.get("ai_decode_tps"), "42")
        migration.backwards(django_apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "36.9")
