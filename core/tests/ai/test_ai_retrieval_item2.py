"""Backlog item 2: semantic advisor-service matching + ranked codebase retrieval."""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.services.ai.codebase_search import query_tokens, rank_entries, tokenize
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.context_builder_service.advisor_semantic import semantic_advisor_matches
from core.services.ai.context_builder_service.codebase_context import (
    CODEBASE_BLOCK_MAX_CHARS,
    build_codebase_block,
    is_codebase_question,
)
from core.services.ai.retrieval import embeddings
from core.views.ai_chat.ai_chat_core_views.generation_pipeline import _infer_question_domain

ADV = ["overview", "cash_flow", "goal_planning", "risk_analysis", "scenario_planner"]
SEM = "core.services.ai.retrieval.semantic_scores"

ENTRIES = [
    {"class_name": "BankCardRenewalFeeService", "location": "core/services/balance/bank_card_renewal.py",
     "module_type": "service", "docstring": "Handles bank card renewal fees", "methods": ["create", "apply"]},
    {"class_name": "ExpenseService", "location": "core/services/expenses/expense_service.py",
     "module_type": "service", "docstring": "Expense CRUD", "methods": ["create_expense"]},
    {"class_name": "Unrelated", "location": "core/utils/misc.py", "module_type": "utility",
     "docstring": "", "methods": []},
]


class AdvisorSemanticTest(SimpleTestCase):
    def test_clear_winner_is_selected(self):
        scores = {"advisor:overview": 0.50, "advisor:cash_flow": 0.48, "advisor:goal_planning": 0.71,
                  "advisor:risk_analysis": 0.49, "advisor:scenario_planner": 0.47}
        with patch(SEM, return_value=scores):
            self.assertEqual(semantic_advisor_matches("can I retire at 55", ADV), ["goal_planning"])

    def test_noise_selects_nothing(self):
        scores = {f"advisor:{k}": v for k, v in zip(ADV, [0.52, 0.49, 0.47, 0.50, 0.51])}
        with patch(SEM, return_value=scores):
            self.assertEqual(semantic_advisor_matches("qzxjklm", ADV), [])

    def test_embedding_outage_and_exception_fall_back(self):
        with patch(SEM, return_value=None):
            self.assertEqual(semantic_advisor_matches("anything", ADV), [])
        with patch(SEM, side_effect=RuntimeError("boom")):
            self.assertEqual(semantic_advisor_matches("anything", ADV), [])

    def test_max_two_and_empty_query(self):
        scores = {"advisor:overview": 0.9, "advisor:cash_flow": 0.8, "advisor:goal_planning": 0.7,
                  "advisor:risk_analysis": 0.1, "advisor:scenario_planner": 0.1}
        with patch(SEM, return_value=scores):
            self.assertEqual(semantic_advisor_matches("x", ADV), ["overview", "cash_flow"])
            self.assertEqual(semantic_advisor_matches("  ", ADV), [])


class QueryCacheTest(SimpleTestCase):
    def test_second_embed_of_same_query_is_cached(self):
        embeddings._query_cache.clear()
        before = embeddings.stats_snapshot()
        with patch.object(embeddings, "_embed", return_value=[1.0, 0.0]) as m:
            embeddings._embed_query("How much can I save?")
            embeddings._embed_query("  how much can i save? ")
        self.assertEqual(m.call_count, 1)
        self.assertEqual(embeddings.stats_delta(before)["query_cache_hits"], 1)


class CodebaseSearchTest(SimpleTestCase):
    def test_tokenize_splits_camel_snake_paths(self):
        self.assertTrue({"bank", "card", "renewal", "fee"} <= tokenize("BankCardRenewalFee"))
        self.assertIn("expense", tokenize("core/services/expenses/expense_service.py"))

    def test_natural_language_query_ranks_right_class_first(self):
        hits = rank_entries(ENTRIES, "where do we handle bank card renewal fees?")
        self.assertEqual(hits[0]["class_name"], "BankCardRenewalFeeService")
        self.assertNotIn("Unrelated", [h["class_name"] for h in hits])

    def test_legacy_exact_term_still_first(self):
        self.assertEqual(rank_entries(ENTRIES, "ExpenseService")[0]["class_name"], "ExpenseService")

    def test_generic_only_query_has_no_tokens(self):
        self.assertEqual(query_tokens("which class handles the code"), set())

    def test_is_codebase_question(self):
        self.assertTrue(is_codebase_question("which class handles bank card renewal fees?"))
        self.assertTrue(is_codebase_question("where is the expense mirroring implemented"))
        self.assertFalse(is_codebase_question("what is my balance?"))
        self.assertFalse(is_codebase_question("my asset class allocation"))

    def test_block_is_bounded_and_none_when_no_hits(self):
        with patch("core.services.ai.context_builder_service.codebase_context.CodebaseIndexer.get_index",
                   return_value={"architecture_index": ENTRIES[:2] * 10}):
            block = build_codebase_block("bank card renewal fee implemented")
        self.assertLessEqual(len(block), CODEBASE_BLOCK_MAX_CHARS)
        with patch("core.services.ai.context_builder_service.codebase_context.CodebaseIndexer.get_index",
                   return_value={"architecture_index": []}):
            self.assertIsNone(build_codebase_block("zzz"))

    def test_gerund_matches_stem(self):
        self.assertIn("mirror", tokenize("mirroring"))

    def test_function_only_module_is_indexed_and_not_counted_as_class(self):
        from core.services.ai.codebase_indexer import CodebaseIndexer
        res = CodebaseIndexer.get_index(search_term="where is the expense mirroring implemented", force_refresh=True)
        names = [h["class_name"] for h in res["architecture_index"][:6]]
        self.assertIn("expense_mirror_engine", names)
        entries = CodebaseIndexer.get_index(force_refresh=True)
        self.assertGreater(entries["total_indexed_classes"], 100)
        mod = [h for h in CodebaseIndexer.get_index(search_term="expense_mirror_engine")["architecture_index"]
               if h.get("kind") == "module"]
        self.assertTrue(mod and "sync_mirror" in mod[0]["methods"])

    def test_real_index_finds_context_builder(self):
        block = build_codebase_block("which class assembles the AI context messages and token budget, ContextBuilderService")
        self.assertIn("ContextBuilderService", block or "")


class DomainInferenceTest(SimpleTestCase):
    def test_word_boundary(self):
        self.assertEqual(_infer_question_domain("show my expense table for the building"), "business_data_analysis")
        self.assertEqual(_infer_question_domain("what tabs does the settings page have"), "app_features_architecture")


class AssembleFallbackTest(TestCase):
    """Fallback branch: nothing lexical/business/code matched."""

    def _sources(self, semantic):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username="u_item2", password="x")
        with patch("core.services.ai.context_builder_service.service.semantic_advisor_matches", return_value=semantic):
            _, sources = ContextBuilderService().assemble_messages("qzxjklm vwplotg", [], user=user)
        return sources

    def test_semantic_match_replaces_default_set(self):
        self.assertEqual(self._sources(["goal_planning"]), ["goal_planning"])

    def test_no_semantic_match_uses_default_set(self):
        self.assertEqual(self._sources([]), ["overview", "cash_flow", "goal_planning", "risk_analysis"])
