"""Semantic retrieval utilities (embeddings + cosine ranking), used as a
bonus signal in providers/registry/scoring.py and
context_builder_service/service.py."""

from core.services.ai.retrieval.embeddings import semantic_scores

__all__ = ["semantic_scores"]
