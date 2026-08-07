"""
Central AI Context Builder service.
Unifies Application Structure, Business Data, Codebase Architecture Index, and User/Settings context.
Decouples AI tools from calling each other directly.

CRITICAL CONSTRAINT: 100% READ-ONLY. Zero write/save/delete calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from django.urls import get_resolver, URLResolver, URLPattern

from core.services.ai.providers import get_relevant_providers_data
from core.services.ai.codebase_indexer import CodebaseIndexer


logger = logging.getLogger(__name__)

_LIVE_STRUCTURE_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 600.0


class AIContextBuilder:
    @classmethod
    def build_structure_context(cls, user: Any, force_refresh: bool = False, include_playwright: bool = False) -> dict[str, Any]:
        """
        3-Tier Application Structure Discovery:
        - Tier 1: Live Django Named Routes from get_resolver()
        - Tier 2: View & Template Metadata Inspection
        - Tier 3: Playwright Live DOM Crawl (targeted on-demand for dynamic tabs/modals)
        """
        now = time.time()
        cached_time = _LIVE_STRUCTURE_CACHE.get("timestamp", 0)

        if not force_refresh and (now - cached_time < _CACHE_TTL_SECONDS) and "data" in _LIVE_STRUCTURE_CACHE:
            res = dict(_LIVE_STRUCTURE_CACHE["data"])
            res["cached"] = True
            return res

        routes_info = cls._get_live_django_routes_with_metadata()

        live_pages = []
        crawl_error = None
        if include_playwright:
            try:
                from core.services.ai.tools import _crawl_live_pages_with_playwright
                live_pages, crawl_error = _crawl_live_pages_with_playwright(base_url="http://127.0.0.1:8001", routes_info=routes_info)
            except Exception as ex:
                logger.warning("Playwright live page crawl failed: %s", ex)
                live_pages = []
                crawl_error = str(ex)

        res_data = {
            "cached": False,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)),
            "total_routes_discovered": len(routes_info),
            "django_routes": routes_info,
            "live_pages": live_pages,
            "playwright_executed": bool(include_playwright and live_pages),
            "crawl_error": crawl_error,
        }

        _LIVE_STRUCTURE_CACHE["timestamp"] = now
        _LIVE_STRUCTURE_CACHE["data"] = res_data
        return res_data

    @classmethod
    def build_business_context(cls, user: Any, search_query: str = "", limit: int = 20) -> dict[str, Any]:
        """Fetch read-only business data signals matching search query intent via Data Provider Registry."""
        return get_relevant_providers_data(user, search_query=search_query, limit=limit)



    @classmethod
    def build_codebase_context(
        cls,
        user: Any,
        search_term: str = "",
        module_type: str = "",
        class_name: str = "",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Fetch codebase architecture index via AST indexer."""
        return CodebaseIndexer.get_index(
            search_term=search_term,
            module_type=module_type,
            class_name=class_name,
            force_refresh=force_refresh,
        )

    @classmethod
    def build_feature_context(cls, user: Any, focus_area: str = "general", gap_description: str = "") -> dict[str, Any]:
        """Assembles unified context via AIContextOrchestrator for BRD suggestion."""
        from core.services.ai.orchestrator import AIContextOrchestrator
        orch_res = AIContextOrchestrator.assemble_context(
            intent="feature_suggestion",
            user=user,
            params={"focus_area": focus_area, "gap_description": gap_description},
        )
        return {
            "focus_area": focus_area,
            "gap_description": gap_description,
            "live_app_structure": orch_res.get("live_app_structure", {}),
            "real_business_data_signals": orch_res.get("business_data", {}),
            "codebase_architecture_signals": orch_res.get("codebase_ast_index", {}),
            "capability_registry": orch_res.get("capability_registry", {}),
            "_explanation_metadata": orch_res.get("_explanation_metadata", {}),
            "required_document_sections": [
                "Problem Statement",
                "Why This Matters",
                "User Story",
                "Acceptance Criteria",
                "Data & Existing Code Reuse Opportunities",
                "Real Gaps / Unknowns",
            ],
            "instructions": (
                "SUGGESTION ONLY: Generate a structured Business Requirements Document based on the provided live application structure, "
                "real business data signals, codebase architecture signals, and capabilities. Ground all proposed features in existing app routes, "
                "reusable backend services/models, and genuine user data gaps. Do NOT output any code, do NOT create files, and do NOT perform any write operations."
            ),
        }

    @classmethod
    def _get_live_django_routes_with_metadata(cls) -> list[dict[str, Any]]:
        """Walks Django's root URL resolver to discover all live named page routes with view metadata."""
        resolver = get_resolver()
        routes: list[dict[str, Any]] = []

        def _walk_patterns(patterns: Any, prefix: str = ""):
            for pattern in patterns:
                if isinstance(pattern, URLPattern):
                    route_str = prefix + str(pattern.pattern)
                    clean_path = "/" + route_str.strip("/")

                    # Exclude static/media/admin/api internal routes
                    if any(clean_path.startswith(p) for p in ["/api/", "/static/", "/media/", "/admin"]):
                        continue

                    view_name = getattr(pattern.callback, "__name__", str(pattern.callback))
                    view_doc = getattr(pattern.callback, "__doc__", "") or ""
                    view_cls = getattr(pattern.callback, "view_class", None)
                    view_class_name = view_cls.__name__ if view_cls else ""

                    routes.append({
                        "name": pattern.name or "",
                        "route": clean_path,
                        "view_name": view_name,
                        "view_class": view_class_name,
                        "docstring": view_doc.strip().split("\n")[0] if view_doc else "",
                    })
                elif isinstance(pattern, URLResolver):
                    sub_prefix = prefix + str(pattern.pattern)
                    _walk_patterns(pattern.url_patterns, prefix=sub_prefix)

        _walk_patterns(resolver.url_patterns)
        return routes
