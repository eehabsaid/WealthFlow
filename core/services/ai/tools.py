from __future__ import annotations

import datetime
import logging
import time
from typing import Any

from core.models import AppSettings
from core.services.financial_advisor.registry import (
    ADVISOR_SERVICE_PROVIDERS,
    get_financial_advisor_payload,
)
from core.services.financial_advisor.scenario_planner_service import (
    ScenarioPlannerService,
    create_scenario_record,
)
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService

logger = logging.getLogger(__name__)

_STRUCTURE_CACHE = {"timestamp": 0.0, "data": None}
CACHE_TTL_SECONDS = 600  # 10 minutes cache TTL


# ── Tool Handlers ─────────────────────────────────────────────────────────────

def _handle_create_scenario(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps atomic scenario creation via create_scenario_record."""
    name = str(params.get("name", "")).strip()
    description = str(params.get("description", "")).strip()
    is_baseline_pinned = bool(params.get("is_baseline_pinned", False))
    events = params.get("events", [])
    sc = create_scenario_record(
        name=name,
        description=description,
        is_baseline_pinned=is_baseline_pinned,
        events=events,
    )
    return sc.to_dict()


def _handle_compare_scenarios(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps ScenarioPlannerService.payload with scenario_ids."""
    scenario_ids = params.get("scenario_ids", [])
    svc = ScenarioPlannerService(user=user)
    return svc.payload(scenario_ids=scenario_ids)


def _handle_summarize_report(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps get_financial_advisor_payload for a service key."""
    service_key = str(params.get("service_key", "")).strip().lower()
    return get_financial_advisor_payload(service_key)


def _handle_explain_chart(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps get_financial_advisor_payload for a service key."""
    service_key = str(params.get("service_key", "")).strip().lower()
    return get_financial_advisor_payload(service_key)


def _handle_suggest_optimizations(user: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Wraps PortfolioOptimizerService and OpportunityDetectionService payloads."""
    focus = str(params.get("focus", "all")).strip().lower()
    res: dict[str, Any] = {}
    if focus in ("all", "portfolio", "portfolio_optimizer"):
        res["portfolio_optimizer"] = PortfolioOptimizerService().payload()
    if focus in ("all", "opportunity", "opportunity_detection"):
        res["opportunity_detection"] = OpportunityDetectionService().payload()
    return res


def _get_live_django_routes() -> list[dict[str, str]]:
    """Walks Django's URL resolver recursively to return real registered named routes."""
    from django.urls import get_resolver, URLPattern, URLResolver

    routes = []
    seen = set()

    def _recurse(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLResolver):
                _recurse(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                path_str = "/" + (prefix + str(p.pattern)).lstrip("^/").rstrip("$")
                clean_path = "/" + path_str.strip("/")
                if clean_path == "/":
                    clean_path = "/"
                if any(clean_path.startswith(x) for x in ("/api/", "/static/", "/media/", "/admin/")):
                    continue
                if clean_path not in seen:
                    seen.add(clean_path)
                    routes.append({
                        "route": clean_path,
                        "name": p.name or "",
                    })

    _recurse(get_resolver().url_patterns)
    return routes


def _crawl_live_pages_with_playwright(base_url: str = "http://127.0.0.1:8001") -> tuple[list[dict[str, Any]], str | None]:
    """
    Crawls live application pages in headless mode using Playwright to inspect rendered DOM.
    Returns (page_structures, crawl_error).
    CRITICAL CONSTRAINT: 100% READ-ONLY safe browsing - inspects DOM elements only, never submits forms or clicks write/delete actions.
    """
    structures = []
    crawl_error = None

    try:
        from playwright.sync_api import sync_playwright
        from tests.core.cdn_fallback import install_cdn_fallback

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            install_cdn_fallback(page)

            # Perform login as eehab_said / Eehabdev1
            page.goto(f"{base_url}/accounts/login/", timeout=8000)
            page.wait_for_load_state("networkidle", timeout=5000)

            if page.query_selector('input[name="username"]'):
                page.fill('input[name="username"]', "eehab_said")
                page.fill('input[name="password"]', "Eehabdev1")
                page.click('button[type="submit"], input[type="submit"], .btn-login')
                page.wait_for_load_state("networkidle", timeout=5000)

            sections = [
                ("dashboard", "Dashboard"),
                ("financial-advisor", "Financial Advisor"),
                ("employment", "Employment"),
                ("balance", "Balance"),
                ("bank-certificates", "Bank Certificates"),
                ("fixed-assets", "Fixed Assets"),
                ("exchange-rates", "Exchange Rates"),
                ("gold-price", "Gold Price"),
                ("expenses", "Expenses"),
                ("expense-categories", "Categories"),
                ("reports", "Reports"),
                ("advanced-reports", "Advanced Reports"),
                ("settings", "Settings"),
            ]

            for route_name, fallback_title in sections:
                url = f"{base_url}/#{route_name}" if route_name != "dashboard" else f"{base_url}/"
                try:
                    page.goto(url, timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=3000)
                    page.wait_for_timeout(200)

                    dom_data = page.evaluate("""() => {
                        const titleEl = document.querySelector('h1, h2, h3, .page-header, .brand-text');
                        const pageTitle = titleEl ? titleEl.textContent.trim() : '';

                        const tabEls = Array.from(document.querySelectorAll(
                            '#main-content button, #main-content .nav-link, #main-content .nav-item, #main-content [role="tab"], #main-content .wf-tab'
                        ));
                        const tabs = [];
                        const seenTabs = new Set();
                        tabEls.forEach(el => {
                            if (el.offsetParent === null || el.closest('.d-none')) return;
                            const text = el.textContent.trim();
                            if (text && text.length < 50 && !seenTabs.has(text.toLowerCase())) {
                                seenTabs.add(text.toLowerCase());
                                tabs.push({ name: text, id: el.id || '' });
                            }
                        });

                        const modalEls = Array.from(document.querySelectorAll(
                            '[data-bs-toggle="modal"], [onclick*="Modal"], [onclick*="show"], .modal-title'
                        ));
                        const modals = [];
                        const seenModals = new Set();
                        modalEls.forEach(el => {
                            const text = (el.textContent || el.getAttribute('title') || el.getAttribute('data-bs-target') || '').trim();
                            if (text && text.length < 50 && !seenModals.has(text.toLowerCase())) {
                                seenModals.add(text.toLowerCase());
                                modals.push(text);
                            }
                        });

                        return { pageTitle, tabs, modals };
                    }""")

                    structures.append({
                        "route": route_name,
                        "title": dom_data.get("pageTitle") or fallback_title,
                        "tabs": dom_data.get("tabs", []),
                        "modals_or_forms": dom_data.get("modals", []),
                    })
                except Exception as page_exc:
                    logger.debug("Failed to inspect route '%s': %s", route_name, page_exc)
                    structures.append({
                        "route": route_name,
                        "title": fallback_title,
                        "tabs": [],
                        "modals_or_forms": [],
                        "error": str(page_exc),
                    })

            browser.close()
    except Exception as exc:
        logger.warning("Playwright live DOM crawl failed: %s", exc)
        crawl_error = f"Playwright crawl error: {exc}"

    return structures, crawl_error


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

    query_type = str(params.get("query_type", "all")).strip().lower()
    focus_area = str(params.get("focus_area", "")).strip().lower()
    limit = min(int(params.get("limit", 20) or 20), 100)

    res = AIContextBuilder.build_business_context(
        user=user,
        query_type=query_type,
        focus_area=focus_area,
        limit=limit,
    )
    if isinstance(res, dict) and "_explanation_metadata" not in res:
        res["_explanation_metadata"] = {
            "intent": "business_analysis",
            "context_sources": ["business_data_providers"],
            "modules_consulted": [k for k in res.keys() if not k.endswith("_error")],
            "confidence": "high",
            "unavailable_context": [k for k in res.keys() if k.endswith("_error")],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }
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


# ── Registered Tools Map & Ollama Schemas ─────────────────────────────────────

AI_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "create_scenario": {
        "name": "create_scenario",
        "description": "Create a new financial scenario with optional events to project future wealth and cash flow impact.",
        "is_read_only": False,
        "domain": "business_data_analysis",
        "handler": _handle_create_scenario,
        "schema": {
            "type": "function",
            "function": {
                "name": "create_scenario",
                "description": "Create a new financial scenario with optional events to project future wealth and cash flow impact.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Scenario name"},
                        "description": {"type": "string", "description": "Scenario description"},
                        "is_baseline_pinned": {"type": "boolean", "description": "Pin as baseline scenario"},
                        "events": {
                            "type": "array",
                            "description": "List of scenario events",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event_type": {"type": "string", "description": "Type key (house, car, salary_change, marriage, child, retirement, inheritance, medical, business, job_loss)"},
                                    "event_date": {"type": "string", "description": "Event date (YYYY-MM-DD)"},
                                    "params": {"type": "object", "description": "Event specific parameters"},
                                    "order": {"type": "integer", "description": "Display order"}
                                },
                                "required": ["event_type", "event_date"]
                            }
                        }
                    },
                    "required": ["name"]
                }
            }
        }
    },
    "compare_scenarios": {
        "name": "compare_scenarios",
        "description": "Compare financial performance, debt, cash flow, and net worth projections across multiple scenarios by ID.",
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_compare_scenarios,
        "schema": {
            "type": "function",
            "function": {
                "name": "compare_scenarios",
                "description": "Compare financial performance, debt, cash flow, and net worth projections across multiple scenarios by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scenario_ids": {
                            "type": "array",
                            "description": "List of scenario IDs to compare",
                            "items": {"type": "integer"}
                        }
                    },
                    "required": ["scenario_ids"]
                }
            }
        }
    },
    "summarize_report": {
        "name": "summarize_report",
        "description": "Fetch real data payload for a financial advisor service (e.g. overview, cash_flow, spending_intelligence, risk_analysis) to summarize.",
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_summarize_report,
        "schema": {
            "type": "function",
            "function": {
                "name": "summarize_report",
                "description": "Fetch real data payload for a financial advisor service to summarize.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_key": {
                            "type": "string",
                            "description": "Service key (overview, cash_flow, wealth_growth, portfolio_optimizer, goal_planning, risk_analysis, spending_intelligence, opportunity_detection, performance, what_if_simulator, scenario_planner)"
                        }
                    },
                    "required": ["service_key"]
                }
            }
        }
    },
    "explain_chart": {
        "name": "explain_chart",
        "description": "Fetch real chart/forecast payload data for a service key to explain what the figures and trends mean.",
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_explain_chart,
        "schema": {
            "type": "function",
            "function": {
                "name": "explain_chart",
                "description": "Fetch real chart/forecast payload data for a service key to explain what figures mean.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_key": {
                            "type": "string",
                            "description": "Service key to fetch chart data for"
                        }
                    },
                    "required": ["service_key"]
                }
            }
        }
    },
    "suggest_optimizations": {
        "name": "suggest_optimizations",
        "description": "Fetch real optimization recommendations from Portfolio Optimizer and Opportunity Detection services.",
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_suggest_optimizations,
        "schema": {
            "type": "function",
            "function": {
                "name": "suggest_optimizations",
                "description": "Fetch real optimization recommendations from Portfolio Optimizer and Opportunity Detection services.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "focus": {
                            "type": "string",
                            "description": "Focus area ('all', 'portfolio', or 'opportunity')",
                            "default": "all"
                        }
                    }
                }
            }
        }
    },
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
        "description": "Fetch real read-only business data across all modules (Salary, Balance, Expenses, Assets, Certificates, Market Rates, Advisor) for cross-module reasoning.",
        "is_read_only": True,
        "domain": "business_data_analysis",
        "handler": _handle_query_application_data,
        "schema": {
            "type": "function",
            "function": {
                "name": "query_application_data",
                "description": "Fetch real read-only business data across all modules for cross-module reasoning.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "description": "Query type ('all', 'financial_position', 'expense_vs_salary', 'asset_net_worth_contribution', 'long_term_growth_categories', 'exchange_rate_correlation', 'cross_module_summary')",
                            "default": "all"
                        },
                        "focus_area": {
                            "type": "string",
                            "description": "Module focus ('all', 'bank_certificates', 'market_data', 'balances', 'fixed_assets', 'salary', 'expenses', 'financial_advisor' or comma-separated list like 'bank_certificates,market_data,balances'). Default is 'all'.",
                            "default": "all"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max records per dataset (default 20, max 100)",
                            "default": 20
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


def get_registered_tool_schemas(domain: str | None = None) -> list[dict[str, Any]]:
    """Returns list of registered tool schemas in Ollama function-calling format, filtered by domain if specified."""
    schemas = []
    for tool_def in AI_TOOL_REGISTRY.values():
        if domain and tool_def.get("domain") != domain:
            continue
        schemas.append(tool_def["schema"])
    return schemas


# ── Validation Pipeline & Execution Engine ───────────────────────────────────

def validate_and_execute_tool(
    tool_name: str,
    params: dict[str, Any] | None,
    user: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Validate tool execution request against 5 mandatory security rules in order:
    1. Tool Registry Check: Unknown tool name -> REJECT
    2. Parameters Schema Check: Invalid/missing/wrong-typed params -> REJECT
    3. Authenticated User Check: Anonymous execution -> REJECT
    4. Authorization Check: Active user auth permission -> REJECT
    5. Business Rules Check: Underlying model/service business rule -> REJECT

    Returns (audit_record, tool_result) tuple.
    Audit record contains:
        - tool: str
        - timestamp: str (ISO format)
        - status: "success" | "failed" | "rejected"
        - duration_ms: int
        - rejection_reason: str (optional)
        - arguments: dict
    Must NEVER put raw exception strings or stack traces into audit record.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_name = str(tool_name or "").strip()
    clean_params = params if isinstance(params, dict) else {}

    # Rule 1: Tool Registry Name Check
    if clean_name not in AI_TOOL_REGISTRY:
        audit = {
            "tool": clean_name or "unknown",
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": f"Unknown tool '{clean_name}'",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": f"Unknown tool '{clean_name}'"}

    tool_def = AI_TOOL_REGISTRY[clean_name]

    fn_schema = tool_def["schema"]["function"]["parameters"]
    required_fields = fn_schema.get("required", [])

    # Rule 2: Parameters Schema Validation
    for field in required_fields:
        if field not in clean_params or clean_params[field] is None:
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Missing required parameter '{field}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Missing required parameter '{field}'"}

    if clean_name == "create_scenario":
        name_val = clean_params.get("name")
        if not isinstance(name_val, str) or not name_val.strip():
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'name' must be a non-empty string",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'name' must be a non-empty string"}
        if "events" in clean_params and not isinstance(clean_params["events"], list):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'events' must be a list",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'events' must be a list"}

    elif clean_name == "compare_scenarios":
        scenario_ids = clean_params.get("scenario_ids")
        if not isinstance(scenario_ids, list):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'scenario_ids' must be a list of integers",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'scenario_ids' must be a list of integers"}
        for item in scenario_ids:
            if not isinstance(item, int) or isinstance(item, bool):
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": "All elements in 'scenario_ids' must be integers",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": "All elements in 'scenario_ids' must be integers"}

    elif clean_name in ("summarize_report", "explain_chart"):
        skey = str(clean_params.get("service_key", "")).strip().lower()
        if skey not in ADVISOR_SERVICE_PROVIDERS:
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid service_key '{skey}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid service_key '{skey}'"}

    elif clean_name == "suggest_optimizations":
        focus = str(clean_params.get("focus", "all")).strip().lower()
        if focus not in ("all", "portfolio", "opportunity", "portfolio_optimizer", "opportunity_detection"):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid focus parameter '{focus}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid focus parameter '{focus}'"}

    elif clean_name == "suggest_app_feature":
        focus_area = clean_params.get("focus_area")
        if not isinstance(focus_area, str) or not focus_area.strip():
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": "Parameter 'focus_area' must be a non-empty string",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": "Parameter 'focus_area' must be a non-empty string"}

    elif clean_name == "query_application_data":
        qtype = str(clean_params.get("query_type", "all")).strip().lower()
        if qtype not in ("all", "financial_position", "expense_vs_salary", "asset_net_worth_contribution", "long_term_growth_categories", "exchange_rate_correlation", "cross_module_summary", "net_worth"):
            audit = {
                "tool": clean_name,
                "timestamp": timestamp,
                "status": "rejected",
                "duration_ms": 0,
                "rejection_reason": f"Invalid query_type parameter '{qtype}'",
                "arguments": clean_params,
            }
            return audit, {"ok": False, "error": f"Invalid query_type parameter '{qtype}'"}

    # Rule 3: Authenticated User Check
    if not user or not getattr(user, "is_authenticated", False):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "User authentication required",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "User authentication required"}

    # Rule 4: Authorization Check
    if not getattr(user, "is_active", True):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "User account is inactive",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "User account is inactive"}

    # Rule 5: Business Rules Validation (e.g. event schema inside create_scenario)
    if clean_name == "create_scenario":
        events = clean_params.get("events") or []
        for idx, ev in enumerate(events):
            if not isinstance(ev, dict):
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": f"Event at index {idx} must be an object",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": f"Event at index {idx} must be an object"}
            etype = str(ev.get("event_type", "")).strip()
            edate = ev.get("event_date")
            if not etype or not edate:
                audit = {
                    "tool": clean_name,
                    "timestamp": timestamp,
                    "status": "rejected",
                    "duration_ms": 0,
                    "rejection_reason": f"Event at index {idx} missing event_type or event_date",
                    "arguments": clean_params,
                }
                return audit, {"ok": False, "error": f"Event at index {idx} missing event_type or event_date"}

    # Global read-only configuration enforcement (evaluated after parameters & auth checks)
    ai_read_only_setting = AppSettings.get("ai_read_only", "true").strip().lower() in ("true", "1", "yes")
    if ai_read_only_setting and not tool_def.get("is_read_only", False):
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "rejected",
            "duration_ms": 0,
            "rejection_reason": "Global AI settings enforce read-only mode.",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "Global AI settings enforce read-only mode."}

    # Validation passed -> Execute handler with duration tracking
    start_time = time.perf_counter()
    handler = tool_def["handler"]

    try:
        result_data = handler(user=user, params=clean_params)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "success",
            "duration_ms": elapsed_ms,
            "arguments": clean_params,
        }
        return audit, {"ok": True, "data": result_data}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning("Tool '%s' execution failed: %s", clean_name, exc, exc_info=True)
        audit = {
            "tool": clean_name,
            "timestamp": timestamp,
            "status": "failed",
            "duration_ms": elapsed_ms,
            "rejection_reason": "Execution error",
            "arguments": clean_params,
        }
        return audit, {"ok": False, "error": "Tool execution failed"}

