"""The query engine's cost estimate uses the current machine's throughput."""

from django.test import TestCase

from ai.models import AISetting
from ai.services.query_engine.llm_slots import estimate_seconds


class ThroughputDefaultsTest(TestCase):
    def test_estimate_uses_the_current_machine_defaults(self):
        AISetting.objects.filter(key__in=("ai_prompt_tps", "ai_decode_tps")).delete()
        self.assertAlmostEqual(estimate_seconds(300, 40), 300 / 2500 + 40 / 62, places=3)
