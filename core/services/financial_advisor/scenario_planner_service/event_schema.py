"""Static backend event schema registry (single source of truth) for
ScenarioPlannerService — drives dynamic scenario event forms on the frontend.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations


# ── Backend Event Schema Registry (Single Source of Truth) ───────────────────
SCENARIO_EVENT_SCHEMA_VERSION = 1

EVENT_SCHEMA = [
    {
        "event_type": "house",
        "label_key": "scenario_planner_event_house",
        "icon": "bi-house-door",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "purchase_price", "label_key": "scenario_planner_field_purchase_price", "type": "number", "default": 3000000, "min": 0},
            {"name": "down_payment", "label_key": "scenario_planner_field_down_payment", "type": "number", "default": 600000, "min": 0},
            {"name": "mortgage_rate_pct", "label_key": "scenario_planner_field_mortgage_rate", "type": "number", "default": 18.0, "min": 0, "max": 100},
            {"name": "term_years", "label_key": "scenario_planner_field_term_years", "type": "number", "default": 20, "min": 1, "max": 40},
            {"name": "monthly_installment", "label_key": "scenario_planner_field_monthly_installment", "type": "number", "default": 35000, "min": 0},
        ],
    },
    {
        "event_type": "car",
        "label_key": "scenario_planner_event_car",
        "icon": "bi-car-front",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "purchase_price", "label_key": "scenario_planner_field_purchase_price", "type": "number", "default": 800000, "min": 0},
            {"name": "down_payment", "label_key": "scenario_planner_field_down_payment", "type": "number", "default": 200000, "min": 0},
            {"name": "monthly_installment", "label_key": "scenario_planner_field_monthly_installment", "type": "number", "default": 15000, "min": 0},
            {"name": "maintenance_monthly", "label_key": "scenario_planner_field_maintenance_monthly", "type": "number", "default": 2000, "min": 0},
        ],
    },
    {
        "event_type": "salary_change",
        "label_key": "scenario_planner_event_salary_change",
        "icon": "bi-graph-up-arrow",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "change_type", "label_key": "scenario_planner_field_change_type", "type": "select", "default": "percentage", "options": ["percentage", "fixed_amount"]},
            {"name": "salary_change_pct", "label_key": "scenario_planner_field_salary_change_pct", "type": "number", "default": 15.0},
            {"name": "salary_change_amount", "label_key": "scenario_planner_field_salary_change_amount", "type": "number", "default": 5000.0},
        ],
    },
    {
        "event_type": "marriage",
        "label_key": "scenario_planner_event_marriage",
        "icon": "bi-heart",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 400000, "min": 0},
            {"name": "new_monthly_expense", "label_key": "scenario_planner_field_new_monthly_expense", "type": "number", "default": 5000, "min": 0},
        ],
    },
    {
        "event_type": "child",
        "label_key": "scenario_planner_event_child",
        "icon": "bi-balloon-heart",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 50000, "min": 0},
            {"name": "new_monthly_expense", "label_key": "scenario_planner_field_new_monthly_expense", "type": "number", "default": 4000, "min": 0},
        ],
    },
    {
        "event_type": "retirement",
        "label_key": "scenario_planner_event_retirement",
        "icon": "bi-umbrella",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "target_age", "label_key": "scenario_planner_field_target_age", "type": "number", "default": 60, "min": 30, "max": 90},
            {"name": "desired_monthly_income", "label_key": "scenario_planner_field_desired_monthly_income", "type": "number", "default": 30000, "min": 0},
        ],
    },
    {
        "event_type": "inheritance",
        "label_key": "scenario_planner_event_inheritance",
        "icon": "bi-gift",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "lump_sum_amount", "label_key": "scenario_planner_field_lump_sum_amount", "type": "number", "default": 1000000, "min": 0},
        ],
    },
    {
        "event_type": "medical",
        "label_key": "scenario_planner_event_medical",
        "icon": "bi-hospital",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 150000, "min": 0},
            {"name": "monthly_ongoing_cost", "label_key": "scenario_planner_field_ongoing_cost", "type": "number", "default": 1500, "min": 0},
        ],
    },
    {
        "event_type": "business",
        "label_key": "scenario_planner_event_business",
        "icon": "bi-briefcase",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "capital_investment", "label_key": "scenario_planner_field_capital_investment", "type": "number", "default": 500000, "min": 0},
            {"name": "monthly_net_profit", "label_key": "scenario_planner_field_monthly_net_profit", "type": "number", "default": 10000},
        ],
    },
    {
        "event_type": "job_loss",
        "label_key": "scenario_planner_event_job_loss",
        "icon": "bi-x-octagon",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "duration_months", "label_key": "scenario_planner_field_duration_months", "type": "number", "default": 6, "min": 1, "max": 36},
        ],
    },
]

