"""Reminder rule actions (add / edit / delete) on the user's own ReminderRule rows."""

from __future__ import annotations

from core.constants import REMINDER_TYPE_CHOICES, SALARY_TRIGGER_CHOICES
from core.models import ReminderRule

from ai.services.actions.common import ActionError, changed_rows, one_of

TYPES = dict(REMINDER_TYPE_CHOICES)
TRIGGERS = dict(SALARY_TRIGGER_CHOICES)


def _row(r: ReminderRule) -> dict:
    return {"id": r.id, "name": r.name, "rule_type": r.rule_type, "days_before": r.days_before, "salary_trigger": r.salary_trigger,
            "salary_day": r.salary_day, "salary_message": r.salary_message, "is_active": r.is_active}


def _clean(values: dict) -> dict:
    out = {}
    if "name" in values:
        name = " ".join(str(values["name"] or "").split())[:200]
        if not name:
            raise ActionError("a reminder needs a `name`")
        out["name"] = name
    if "rule_type" in values:
        if values["rule_type"] not in TYPES:
            raise ActionError("`rule_type` must be one of: " + ", ".join(TYPES))
        out["rule_type"] = values["rule_type"]
    if "salary_trigger" in values:
        if values["salary_trigger"] not in TRIGGERS:
            raise ActionError("`salary_trigger` must be one of: " + ", ".join(TRIGGERS))
        out["salary_trigger"] = values["salary_trigger"]
    for key, low, high in (("days_before", 0, 365), ("salary_day", 1, 31)):
        if key in values:
            try:
                number = int(values[key])
            except (TypeError, ValueError):
                raise ActionError(f"`{key}` must be a whole number") from None
            if not low <= number <= high:
                raise ActionError(f"`{key}` must be between {low} and {high}")
            out[key] = number
    if "salary_message" in values:
        out["salary_message"] = " ".join(str(values["salary_message"] or "").split())[:300]
    if "is_active" in values:
        out["is_active"] = values["is_active"] in (True, "true", "True", 1)
    return out


def find(user, target: dict) -> ReminderRule:
    qs = ReminderRule.objects.filter(owner=user)
    if target.get("id"):
        qs = qs.filter(pk=target["id"])
    elif target.get("name"):
        qs = qs.filter(name__icontains=str(target["name"]).strip())
    else:
        raise ActionError("say which reminder: target.id or target.name")
    rows = [{"id": r.id, "label": f"#{r.id} {r.name}"} for r in qs[:6]]
    return qs.get(pk=one_of(rows, "reminder")["id"])


def propose(user, op: str, target: dict, values: dict) -> dict:
    if op == "add":
        if not values.get("name"):
            raise ActionError("a reminder needs a `name`")
        clean = _clean({"rule_type": "custom", **values})
        return {"record": "reminder", "op": "add", "params": {"data": clean}, "rows": [{"label": k, "value": str(v)} for k, v in clean.items()]}
    rule = find(user, target)
    current = _row(rule)
    if op == "delete":
        return {"record": "reminder", "op": "delete", "params": {"id": rule.id}, "rows": [{"label": "name", "value": rule.name}, {"label": "rule_type", "value": rule.rule_type}]}
    clean = _clean(values)
    rows = changed_rows(current, clean)
    if not rows:
        raise ActionError("nothing would change; ask the user what to change")
    return {"record": "reminder", "op": "edit", "params": {"id": rule.id, "data": clean}, "rows": rows}


def execute(user, op: str, params: dict) -> str:
    if op == "add":
        rule = ReminderRule.objects.create(owner=user, **params["data"])
        return f"Reminder #{rule.id} added."
    rule = ReminderRule.objects.filter(owner=user, pk=params["id"]).first()
    if rule is None:
        raise ActionError("That reminder no longer exists.")
    if op == "delete":
        rule.delete()
        return f"Reminder #{params['id']} deleted."
    for key, value in params["data"].items():
        setattr(rule, key, value)
    rule.save()
    return f"Reminder #{rule.id} updated."
