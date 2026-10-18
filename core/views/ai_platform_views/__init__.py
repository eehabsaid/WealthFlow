"""
AI Platform & Model Lifecycle Views.

Endpoints for Knowledge Base management and Autonomous Scans.

Split into a package (200-line rule):
  - auth.py                 : _api_auth_required
  - knowledge_views.py       : AIPlatformKnowledgeView, AIPlatformKnowledgeDetailView
  - __init__.py (this file)  : umbrella re-export, preserving the exact
    import surface core/views/exports_ai_features.py already depends on
"""

from core.views.ai_platform_views.knowledge_views import (
    AIPlatformKnowledgeView,
    AIPlatformKnowledgeDetailView,
)

__all__ = [
    "AIPlatformKnowledgeView",
    "AIPlatformKnowledgeDetailView",
]
