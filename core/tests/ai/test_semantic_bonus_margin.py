"""Regression: apply_semantic_bonus must not treat a uniformly-noisy similarity
distribution as a real match.

Reported by Ehab: on a real Ollama box, test_context_builder_service_budget_and_topic_relevance
failed — a nonsense query ("qzxjklm vwplotg") that should fall back to
DEFAULT_CORE_SERVICES instead got matched to "bank_certificates". Root cause:
raw cosine similarity from embedding models (nomic-embed-text included) is
anisotropic — unrelated text pairs commonly score 0.4-0.6, clearing the old
absolute SEMANTIC_MATCH_THRESHOLD (0.45) by noise alone. The sandbox here has
no reachable Ollama, so semantic_scores() always returned None there and this
never reproduced locally — hence a mocked test, not a live-Ollama one.
"""

from unittest.mock import patch

from django.test import TestCase

from core.services.ai.providers.registry.scoring_semantic import (
    SEMANTIC_MATCH_THRESHOLD,
    apply_semantic_bonus,
)


class ApplySemanticBonusTest(TestCase):
    def _run(self, sem_scores, base_scores=None):
        scores = dict(base_scores or {k: 0.0 for k in sem_scores})
        with patch(
            "core.services.ai.retrieval.semantic_scores", return_value=sem_scores
        ):
            apply_semantic_bonus(scores, {k: object() for k in sem_scores}, "some query", lambda p: "meta")
        return scores

    def test_uniformly_noisy_scores_get_no_bonus(self):
        """The exact failure Ehab hit: every candidate clears the absolute
        threshold by roughly the same (noise-floor) amount — no real winner."""
        sem_scores = {"bank_certificates": 0.52, "expenses": 0.49, "balance": 0.47, "overview": 0.50}
        result = self._run(sem_scores)
        self.assertTrue(all(v >= SEMANTIC_MATCH_THRESHOLD for v in sem_scores.values()))
        # None should have gotten a bonus — nothing meaningfully separates from the pack.
        self.assertTrue(all(v == 0.0 for v in result.values()))

    def test_genuine_outlier_still_gets_the_bonus(self):
        """A real topical match separates clearly from the rest of the pack —
        must still pass through."""
        sem_scores = {"certificates": 0.85, "expenses": 0.30, "balance": 0.28, "overview": 0.25}
        result = self._run(sem_scores)
        self.assertGreater(result["certificates"], 0.0)
        self.assertEqual(result["expenses"], 0.0)
        self.assertEqual(result["balance"], 0.0)
        self.assertEqual(result["overview"], 0.0)

    def test_margin_filters_a_case_that_would_pass_under_threshold_alone(self):
        """All three clear the absolute SEMANTIC_MATCH_THRESHOLD (0.45) — under the
        old threshold-only check every one of them would count as a "match".
        The margin-over-mean requirement correctly rejects all of them since
        none meaningfully separates from the pack."""
        sem_scores = {"a": 0.50, "b": 0.48, "c": 0.47}
        self.assertTrue(all(v >= SEMANTIC_MATCH_THRESHOLD for v in sem_scores.values()))
        result = self._run(sem_scores)
        self.assertTrue(all(v == 0.0 for v in result.values()))

    def test_lexical_decisive_skips_semantic_entirely(self):
        scores = {"expenses": 5.0, "balance": 0.0}
        with patch("core.services.ai.retrieval.semantic_scores") as mock_sem:
            apply_semantic_bonus(scores, {"expenses": object(), "balance": object()}, "query", lambda p: "meta")
            mock_sem.assert_not_called()
        self.assertEqual(scores, {"expenses": 5.0, "balance": 0.0})
