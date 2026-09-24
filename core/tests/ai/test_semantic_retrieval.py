"""Tests for semantic retrieval. Mocked embedding calls only — no live
Ollama dependency."""

from unittest.mock import patch

from django.test import TestCase

from core.services.ai.retrieval.embeddings import _candidate_cache, semantic_scores


class SemanticScoresTest(TestCase):
    def setUp(self):
        _candidate_cache.clear()

    def _mock_embed(self, mapping):
        """mapping: {text: vector}. Returns None for anything not listed,
        simulating a real embedding call for known inputs."""

        def fake_embed(text):
            return mapping.get(text)

        return fake_embed

    def test_returns_none_when_embedding_service_unavailable(self):
        with patch("core.services.ai.retrieval.embeddings._embed", return_value=None):
            result = semantic_scores("query", {"a": "desc a"})
        self.assertIsNone(result)

    def test_ranks_by_cosine_similarity(self):
        vectors = {
            "how much interest will I earn next": [1.0, 0.0],
            "certificate interest posting schedule": [1.0, 0.0],  # identical -> sim 1.0
            "unrelated topic about weather": [0.0, 1.0],  # orthogonal -> sim 0.0
        }
        with patch("core.services.ai.retrieval.embeddings._embed", side_effect=self._mock_embed(vectors)):
            result = semantic_scores(
                "how much interest will I earn next",
                {"certificates": "certificate interest posting schedule", "weather": "unrelated topic about weather"},
            )
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["certificates"], 1.0, places=4)
        self.assertAlmostEqual(result["weather"], 0.0, places=4)

    def test_candidate_embeddings_are_cached(self):
        call_count = {"n": 0}

        def counting_embed(text):
            call_count["n"] += 1
            return [1.0, 0.0]

        with patch("core.services.ai.retrieval.embeddings._embed", side_effect=counting_embed):
            semantic_scores("q1", {"a": "desc a"})
            semantic_scores("q2", {"a": "desc a"})

        # 2 query embeds + only 1 candidate embed (second call hits the cache)
        self.assertEqual(call_count["n"], 3)

    def test_missing_candidate_embedding_aborts_to_none(self):
        vectors = {"query": [1.0, 0.0]}
        with patch("core.services.ai.retrieval.embeddings._embed", side_effect=self._mock_embed(vectors)):
            result = semantic_scores("query", {"a": "unembeddable desc"})
        self.assertIsNone(result)
