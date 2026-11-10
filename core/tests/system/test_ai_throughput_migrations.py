"""Core migrations that refresh the host's AI throughput settings."""

from importlib import import_module

from django.apps import apps
from django.test import TestCase

from core.models import AppSettings


class AIThroughputMigrationTests(TestCase):
    def test_refresh_migration_replaces_only_the_old_defaults(self):
        migration = import_module("core.migrations.0035_refresh_ai_throughput_settings")
        AppSettings.set("ai_prompt_tps", "36.9")
        AppSettings.set("ai_decode_tps", "42")
        migration.forwards(apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "700")
        self.assertEqual(AppSettings.get("ai_decode_tps"), "42")
        migration.backwards(apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "36.9")

    def test_measured_migration_replaces_only_the_previous_estimates(self):
        migration = import_module("core.migrations.0037_measured_ai_throughput_settings")
        AppSettings.set("ai_prompt_tps", "700")
        AppSettings.set("ai_decode_tps", "45")
        migration.forwards(apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "2500")
        self.assertEqual(AppSettings.get("ai_decode_tps"), "45")
        migration.backwards(apps, None)
        self.assertEqual(AppSettings.get("ai_prompt_tps"), "700")
