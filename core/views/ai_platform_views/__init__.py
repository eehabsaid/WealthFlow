"""
AI Platform & Model Lifecycle Views.

Endpoints for Knowledge Base management, Autonomous Scans, Dataset Validation,
Model Version Control, Pluggable Training Triggers, and Pre-Promotion Benchmarks.

Split into a package (200-line rule):
  - auth.py                 : _api_auth_required
  - knowledge_views.py       : AIPlatformKnowledgeView, AIPlatformKnowledgeDetailView
  - dataset_model_views.py   : AIPlatformDatasetView, AIPlatformModelView
  - benchmark_views.py       : AIPlatformBenchmarkView
  - __init__.py (this file)  : umbrella re-export, preserving the exact
    import surface core/views/exports_ai_features.py already depends on
"""

from core.views.ai_platform_views.knowledge_views import (
    AIPlatformKnowledgeView,
    AIPlatformKnowledgeDetailView,
)
from core.views.ai_platform_views.dataset_model_views import (
    AIPlatformDatasetView,
    AIPlatformModelView,
)
from core.views.ai_platform_views.benchmark_views import AIPlatformBenchmarkView

__all__ = [
    "AIPlatformKnowledgeView",
    "AIPlatformDatasetView",
    "AIPlatformModelView",
    "AIPlatformBenchmarkView",
    "AIPlatformKnowledgeDetailView",
]
