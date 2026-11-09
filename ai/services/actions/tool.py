"""The propose_action tool the chat model calls to add / edit / delete the user's records (with a confirmation card)."""

from __future__ import annotations

from ai.services.actions import propose_action
from ai.services.actions.charts import CHARTS, show_chart

NAME = "propose_action"
_DESC = ("Propose to ADD, EDIT or DELETE one of the user's records. This only shows a confirmation card under your answer; "
         "NOTHING is saved until the user presses Confirm, so never say it is done. Use it when the user asks you to add / change / remove "
         "an expense, a reminder, or a salary entry. record=expense (add/edit/delete), reminder (add/edit/delete), income (edit/delete a salary entry). "
         "values: expense {amount, currency (code), date YYYY-MM-DD, description, category, subcategory, payment_method Cash|Card|Bank Transfer|Other, bank, notes}; "
         "reminder {name, rule_type, days_before, salary_trigger, salary_day, salary_message, is_active}; income {expected, paid, bonus, notes}. "
         "target (edit/delete) = {id} or, for an expense {date, amount, description}, for a salary entry {year, month}, for a reminder {name}. "
         "Never guess a missing amount, name or target: ask the user. If the tool returns an error, read it and ask the user.")

TOOL_DEF = {
    "name": NAME, "description": _DESC, "is_read_only": True, "tier": "read", "domain": "actions", "offer_all_domains": True,
    "handler": lambda user, params: propose_action(user, params),
    "schema": {"type": "function", "function": {"name": NAME, "description": _DESC, "parameters": {"type": "object", "properties": {
        "record": {"type": "string", "enum": ["expense", "reminder", "income"]},
        "op": {"type": "string", "enum": ["add", "edit", "delete"]},
        "target": {"type": "object", "description": "which existing record (edit / delete)"},
        "values": {"type": "object", "description": "the fields to set (add / edit)"},
    }, "required": ["record", "op"]}}},
}

CHART_NAME = "show_chart"
_CHART_DESC = ("Draw a chart under your answer from the user's REAL data (the numbers are computed by the app, you cannot supply them). "
               "chart: expenses_by_category (pie, a year or one month), expenses_by_month (bars, a year), salary_by_month (line, a year). "
               "Use it when the user asks for a chart, graph or visual, or when a chart clearly helps.")
CHART_TOOL_DEF = {
    "name": CHART_NAME, "description": _CHART_DESC, "is_read_only": True, "tier": "read", "domain": "actions", "offer_all_domains": True,
    "handler": lambda user, params: show_chart(user, params),
    "schema": {"type": "function", "function": {"name": CHART_NAME, "description": _CHART_DESC, "parameters": {"type": "object", "properties": {
        "chart": {"type": "string", "enum": list(CHARTS)},
        "year": {"type": "integer", "description": "defaults to the current year"},
        "month": {"type": "integer", "description": "1-12, only for expenses_by_category"},
    }, "required": ["chart"]}}},
}
