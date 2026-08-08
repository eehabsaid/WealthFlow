"""
Central AI Context Orchestrator.
Assembles intent-driven, unified context payloads across UI structure, Business Data Providers,
Codebase AST Index, and Capability Registry with diagnostic explanation metadata.

CRITICAL CONSTRAINT: 100% READ-ONLY. Zero DB write calls.
"""

from __future__ import annotations

import time
from typing import Any
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.capability_registry import CapabilityRegistry
from core.services.ai.codebase_indexer import CodebaseIndexer
from core.services.ai.providers.registry import get_all_providers_data


class AIContextOrchestrator:
    SUPPORTED_INTENTS = {
        "business_analysis": ["business_data_providers", "capability_registry", "system_knowledge_manifest"],
        "feature_suggestion": ["live_app_structure", "business_data_providers", "codebase_ast_index", "capability_registry", "system_knowledge_manifest"],
        "architecture_question": ["codebase_ast_index", "capability_registry", "live_app_structure", "system_knowledge_manifest"],
        "codebase_question": ["codebase_ast_index", "capability_registry", "system_knowledge_manifest"],
        "financial_advice": ["business_data_providers", "capability_registry", "system_knowledge_manifest"],
    }


    @classmethod
    def assemble_context(
        cls,
        intent: str,
        user: Any,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Assembles unified context payload for the specified intent.
        Returns data payload with _explanation_metadata.
        """
        clean_params = params if isinstance(params, dict) else {}
        clean_intent = str(intent or "business_analysis").strip().lower()
        if clean_intent not in cls.SUPPORTED_INTENTS:
            clean_intent = "business_analysis"

        cache_mgr = AICacheManager()
        cache_key = f"orchestrator_context:{clean_intent}:{user.id if user else 0}:{hash(str(sorted(clean_params.items())))}"
        force_refresh = bool(clean_params.get("force_refresh", False))

        if not force_refresh:
            cached_val = cache_mgr.get(cache_key)
            if cached_val is not None:
                return cached_val

        sources_needed = cls.SUPPORTED_INTENTS[clean_intent]
        context_sources: list[str] = []
        modules_consulted: list[str] = []
        unavailable_context: list[str] = []
        payload_data: dict[str, Any] = {}

        focus_area = str(clean_params.get("focus_area", "")).strip().lower()
        search_term = str(clean_params.get("search_term", "")).strip()

        # 1. Live App Structure
        if "live_app_structure" in sources_needed:
            try:
                from core.services.ai.context_builder import AIContextBuilder
                struct = AIContextBuilder.build_structure_context(
                    user=user,
                    force_refresh=force_refresh,
                    include_playwright=bool(clean_params.get("include_playwright", False)),
                )
                payload_data["live_app_structure"] = struct
                context_sources.append("live_app_structure")
            except Exception as exc:
                unavailable_context.append(f"live_app_structure ({exc})")

        # 2. Business Data Providers
        if "business_data_providers" in sources_needed:
            try:
                limit_val = clean_params.get("limit", None)
                limit = int(limit_val) if limit_val is not None and str(limit_val).isdigit() else None
                bus_data = get_all_providers_data(user=user, limit=limit)
                payload_data["business_data"] = bus_data
                context_sources.append("business_data_providers")
                modules_consulted.extend([k for k in bus_data.keys() if not k.endswith("_error")])
            except Exception as exc:
                unavailable_context.append(f"business_data_providers ({exc})")

        # 3. Codebase AST Index
        if "codebase_ast_index" in sources_needed:
            try:
                code_index = CodebaseIndexer.get_index(
                    search_term=search_term or focus_area,
                    module_type=str(clean_params.get("module_type", "")).strip(),
                    class_name=str(clean_params.get("class_name", "")).strip(),
                    force_refresh=force_refresh,
                )
                payload_data["codebase_ast_index"] = code_index
                context_sources.append("codebase_ast_index")
            except Exception as exc:
                unavailable_context.append(f"codebase_ast_index ({exc})")

        # 4. Capability Registry
        if "capability_registry" in sources_needed:
            try:
                caps = CapabilityRegistry.get_capabilities(search_term=search_term or focus_area)
                payload_data["capability_registry"] = caps
                context_sources.append("capability_registry")
            except Exception as exc:
                unavailable_context.append(f"capability_registry ({exc})")

        # 5. System Knowledge Manifest
        if "system_knowledge_manifest" in sources_needed:
            try:
                from core.services.ai.system_knowledge_engine import SystemKnowledgeEngine
                manifest = SystemKnowledgeEngine.load_manifest()
                payload_data["system_knowledge_manifest"] = manifest
                context_sources.append("system_knowledge_manifest")
            except Exception as exc:
                unavailable_context.append(f"system_knowledge_manifest ({exc})")


        confidence = "high"
        if unavailable_context:
            confidence = "medium" if len(context_sources) > len(unavailable_context) else "low"

        explanation_metadata = {
            "intent": clean_intent,
            "context_sources": context_sources,
            "modules_consulted": sorted(list(set(modules_consulted))),
            "confidence": confidence,
            "unavailable_context": unavailable_context,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }

        result = {
            **payload_data,
            "_explanation_metadata": explanation_metadata,
        }

        cache_mgr.set(cache_key, result, ttl_seconds=600.0)
        return result
