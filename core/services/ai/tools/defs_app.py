"""
AI Tool Registry definitions — App Structure & Codebase Inspection group.

NOTE (200-line file convention): part of the core/services/ai/tools/
package. Paired with defs_scenario.py; the two dicts are merged into
AI_TOOL_REGISTRY in defs.py. If either grows past 200 lines, split further
by tool name within this package.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.tools.data_codebase import (
    _handle_read_live_app_structure,
    _handle_suggest_app_feature,
    _handle_query_application_data,
    _handle_read_application_codebase,
)

APP_TOOL_DEFS: dict[str, dict[str, Any]] = {
    "read_live_app_structure": {
        "name": "read_live_app_structure",
        "description": "Inspect real, live Django routes and DOM rendered tabs/modals to answer what pages and features currently exist.",
        "is_read_only": True,
        "domain": "app_features_architecture",
        "handler": _handle_read_live_app_structure,
        "schema": {
            "type": "function",
            "function": {
                "name": "read_live_app_structure",
                "description": "Inspect real, live Django routes and DOM rendered tabs/modals to answer what pages and features currently exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "force_refresh": {
                            "type": "boolean",
                            "description": "Bypass short 10-minute cache and force a live re-crawl.",
                            "default": False
                        }
                    }
                }
            }
        }
    },
    "suggest_app_feature": {
        "name": "suggest_app_feature",
        "description": "Assemble live app structure and business data signals to produce a structured Business Requirement Document for a proposed feature.",
        "is_read_only": True,
        "domain": "app_features_architecture",
        "handler": _handle_suggest_app_feature,
        "schema": {
            "type": "function",
            "function": {
                "name": "suggest_app_feature",
                "description": "Assemble live app structure and business data signals to produce a structured Business Requirement Document for a proposed feature.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "focus_area": {
                            "type": "string",
                            "description": "Scope of suggestion (e.g. 'financial_advisor', 'balance', 'salary', 'expenses', 'fixed_assets', 'general')",
                            "default": "general"
                        },
                        "gap_description": {
                            "type": "string",
                            "description": "Optional user description of perceived gap or opportunity."
                        }
                    },
                    "required": ["focus_area"]
                }
            }
        }
    },
    "query_application_data": {
        "name": "query_application_data",
        "description": (
            "Fetch real read-only business data across relevant modules based on user intent and "
            "search query. Covers balance/bank accounts, bank certificates, expenses, salary/employment, "
            "fixed assets (real estate, vehicles, physical gold holdings), and market data (live exchange "
            "rates, live gold spot price). ALWAYS call this before answering any question that needs a "
            "specific figure, quantity, or current value the user owns or holds — never estimate or recall "
            "such a figure from general knowledge."
        ),
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_query_application_data,
        "schema": {
            "type": "function",
            "function": {
                "name": "query_application_data",
                "description": (
                    "Fetch real read-only business data across relevant modules matching the search "
                    "query — e.g. 'how much gold do I own', 'my bank balances', 'recent expenses', "
                    "'salary history', 'fixed assets value'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Natural-language search terms or query describing the required financial data (e.g. 'liquid bank deposits certificates gold real estate portfolio')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Optional max records limit per dataset (default is null/unlimited to return full user dataset)"
                        }
                    }
                }
            }
        }
    },

    "read_application_codebase": {
        "name": "read_application_codebase",
        "description": "Inspect structural AST index of codebase classes, services, models, views, docstrings, methods, and dependencies to answer architectural reuse questions.",
        "is_read_only": True,
        "domain": "app_features_architecture",
        "handler": _handle_read_application_codebase,
        "schema": {
            "type": "function",
            "function": {
                "name": "read_application_codebase",
                "description": "Inspect structural AST index of codebase classes, services, models, views, docstrings, methods, and dependencies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Keyword to search across class names, docstrings, methods, and locations (e.g. 'ExpenseService', 'Opportunity', 'CAGR')"
                        },
                        "module_type": {
                            "type": "string",
                            "description": "Filter by architectural component ('service', 'model', 'view', 'serializer', 'integration', 'utility')"
                        },
                        "class_name": {
                            "type": "string",
                            "description": "Filter by class name substring"
                        },
                        "force_refresh": {
                            "type": "boolean",
                            "description": "Bypass short cache and force a live AST scan",
                            "default": False
                        }
                    }
                }
            }
        }
    },
}
