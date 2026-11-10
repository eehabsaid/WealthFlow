"""
AI Tool Registry definitions — What-if scenario tool.

NOTE (200-line file convention): part of the ai/services/tools/
package. The what_if_scenario def lives here so defs_scenario.py stays
under the 200-line limit; defs.py merges WHATIF_TOOL_DEFS into
AI_TOOL_REGISTRY.
"""

from __future__ import annotations

from typing import Any

from core.ai_pack.tools.whatif_scenario import _handle_what_if_scenario

WHATIF_TOOL_DEFS: dict[str, dict[str, Any]] = {
    "what_if_scenario": {
        "name": "what_if_scenario",
        "description": (
            "Simulate hypothetical financial changes (salary raise/cut, expense increase/decrease, "
            "gold allocation target, certificate cashout) against the user's REAL data and return "
            "baseline vs adjusted net worth, risk score and cash coverage. Read-only: never modifies "
            "records. Use for 'what if my salary rises 15%', 'if expenses grow 2000 monthly', "
            "'compare cutting expenses 10% vs raising income 10%', or goal-completion questions "
            "(pass goal_name + extra_monthly_savings)."
        ),
        "is_read_only": True,
        "tier": "read",
        "domain": "business_data_analysis",
        "handler": _handle_what_if_scenario,
        "schema": {
            "type": "function",
            "function": {
                "name": "what_if_scenario",
                "description": (
                    "Simulate one or more hypothetical financial changes against the user's real data "
                    "(read-only). Returns baseline, adjusted and delta for net worth, risk score and "
                    "cash coverage, plus an optional goal-completion estimate."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scenarios": {
                            "type": "array",
                            "description": "One or more hypothetical scenarios to evaluate (and compare). Omit when asking a goal-only question (goal_name + extra_monthly_savings).",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "salary_change_pct": {
                                        "type": "number",
                                        "description": "Percentage change to monthly salary, -100 to +100 (e.g. 15 for a 15% raise).",
                                    },
                                    "expenses_change_pct": {
                                        "type": "number",
                                        "description": "Percentage change to monthly expenses, -50 to +100 (e.g. -10 to cut 10%).",
                                    },
                                    "gold_allocation_target_pct": {
                                        "type": "number",
                                        "description": "Target gold allocation as % of net worth (0 to slider max).",
                                    },
                                    "certificate_reinvestment_choice": {
                                        "type": "string",
                                        "enum": ["reinvest", "cashout"],
                                        "description": "Certificate reinvestment choice (default 'reinvest').",
                                    },
                                },
                            },
                        },
                        "goal_name": {
                            "type": "string",
                            "description": "Optional: name of the user's goal to estimate completion for.",
                        },
                        "extra_monthly_savings": {
                            "type": "number",
                            "description": "Optional: extra amount saved each month, used with goal_name to estimate months-to-goal.",
                        },
                    },
                    "required": [],
                },
            },
        },
    },
}
