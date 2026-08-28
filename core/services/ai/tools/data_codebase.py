"""
AI Tool Handlers — Application Data & Codebase inspection group.

NOTE (200-line file convention): part of the core/services/ai/tools/
package (see tools/__init__.py for the full convention). If this file
grows past 200 lines, split it further into more files within this same
package.
"""

from __future__ import annotations

import time
from typing import Any


def _handle_read_live_app_structure(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Read-only discovery of live app routes and DOM tabs/sections via AIContextBuilder.
    """
    from core.services.ai.context_builder import AIContextBuilder

    force_refresh = bool(params.get("force_refresh", False))
    include_playwright = bool(params.get("include_playwright", False))

    res = AIContextBuilder.build_structure_context(
        user=user,
        force_refresh=force_refresh,
        include_playwright=include_playwright,
    )
    if isinstance(res, dict) and "_explanation_metadata" not in res:
        res["_explanation_metadata"] = {
            "intent": "app_features_architecture",
            "context_sources": ["live_app_structure"],
            "modules_consulted": ["URLResolver", "PlaywrightDOM"],
            "confidence": "high",
            "unavailable_context": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }
    return res


def _handle_query_application_data(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Read-only multi-module business data query service via AIContextBuilder and Data Provider Layer.
    CRITICAL CONSTRAINT: 100% READ-ONLY. Zero write/save/delete calls.
    """
    from core.services.ai.context_builder import AIContextBuilder

    search_query = str(params.get("search_query") or params.get("query") or params.get("focus_area") or "").strip()
    limit_val = params.get("limit")
    limit = int(limit_val) if limit_val is not None and str(limit_val).isdigit() else None

    res = AIContextBuilder.build_business_context(
            user=user,
            search_query=search_query,
            limit=limit,
        )
    if isinstance(res, dict) and "_explanation_metadata" not in res:
        res["_explanation_metadata"] = {
            "intent": "business_analysis",
            "search_query": search_query,
            "context_sources": ["business_data_providers"],
            "modules_consulted": [k for k in res.keys() if not k.endswith("_error")],
            "confidence": "high",
            "unavailable_context": [k for k in res.keys() if k.endswith("_error")],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }
    if isinstance(res, dict):
        res["instructions"] = (
            "CRITICAL ACCURACY RULE: Only report values that literally appear in this data. "
            "For any 'latest'/'most recent'/'newest' request on a list field (e.g. recent_expenses, "
            "recent_transactions), the correct answer is ALWAYS the item at list index 0 — every such "
            "list here is already sorted newest-first. Do NOT group, aggregate, average, or invent "
            "per-month/per-period values unless a field explicitly labeled as monthly/period totals is "
            "present in the data. If asked for a single latest value, quote the id, date, amount, and "
            "category fields exactly as they appear in index 0 of the relevant list — do not paraphrase "
            "or estimate the number. "
            "NO CROSS-DOMAIN MIXING: this response may contain data from several top-level keys "
            "(e.g. 'expenses', 'salary', 'balance', 'bank_certificates') if multiple modules matched "
            "the search query. Each top-level key is a SEPARATE data domain. When the user asks about "
            "expenses specifically, use ONLY the 'expenses' key's data (and its nested 'recent_expenses' "
            "list) — never substitute a value, company name, or amount from 'salary', 'bank_certificates', "
            "or any other key, even if it looks similar or more recent. If the 'expenses' key is absent "
            "from this response, say plainly that no expense data was found rather than using another "
            "domain's data as a stand-in."
        )
    return res



def _handle_suggest_app_feature(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Assembles real live app structure, business data signals, and codebase architecture signals via AIContextBuilder to produce a Business Requirement Document suggestion.
    CRITICAL CONSTRAINT: SUGGESTION ONLY. Never creates code, files, or modifies the app.
    """
    from core.services.ai.context_builder import AIContextBuilder

    focus_area = str(params.get("focus_area", "general")).strip().lower()
    gap_description = str(params.get("gap_description", "")).strip()

    return AIContextBuilder.build_feature_context(
        user=user,
        focus_area=focus_area,
        gap_description=gap_description,
    )


def _handle_read_application_codebase(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """
    Read-only inspection of application codebase architecture (models, services, views, serializers, integrations, utilities).
    CRITICAL CONSTRAINT: 100% READ-ONLY. Zero write/save/delete calls.
    """
    from core.services.ai.context_builder import AIContextBuilder

    search_term = str(params.get("search_term", "")).strip()
    module_type = str(params.get("module_type", "")).strip()
    class_name = str(params.get("class_name", "")).strip()
    force_refresh = bool(params.get("force_refresh", False))

    res = AIContextBuilder.build_codebase_context(
        user=user,
        search_term=search_term,
        module_type=module_type,
        class_name=class_name,
        force_refresh=force_refresh,
    )
    if isinstance(res, dict) and "_explanation_metadata" not in res:
        res["_explanation_metadata"] = {
            "intent": "codebase_question",
            "context_sources": ["codebase_ast_index"],
            "modules_consulted": [module_type] if module_type else ["all_codebase_modules"],
            "confidence": "high",
            "unavailable_context": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }
    return res
