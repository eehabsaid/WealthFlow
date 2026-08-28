"""
AI Tool Registry definitions — Scenario, Report & Optimization group.

NOTE (200-line file convention): part of the core/services/ai/tools/
package. Paired with defs_app.py; the two dicts are merged into
AI_TOOL_REGISTRY in defs.py. If either grows past 200 lines, split further
by tool name within this package.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.tools.scenario import (
    _handle_create_scenario,
    _handle_compare_scenarios,
    _handle_summarize_report,
    _handle_explain_chart,
    _handle_suggest_optimizations,
)

SCENARIO_TOOL_DEFS: dict[str, dict[str, Any]] = {
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
}
