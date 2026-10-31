"""Category 10: budgets and goals. Budget spend is the app's own BudgetService.list_with_spend; goal figures are the stored target and saved
amounts. Named in the question only when the name is unique."""

from __future__ import annotations

from collections import Counter

from core.services.budgets.budget_service import BudgetService

from ..fam_util import dec, expand, money, nonzero, percent, rows, unique_names


def _budgets(user) -> list:
    qs = rows(user, "Budget")
    if qs is None:
        return []
    names = Counter(b["name"] for b in BudgetService.list_with_spend(user))
    return [b for b in BudgetService.list_with_spend(user) if b.get("is_active", True) and b["name"] and names[b["name"]] == 1]


def train(user, langs, rng) -> list:
    out = []
    for b in _budgets(user):
        if nonzero([b["spent_base"]]):
            out += expand(f"budget_used:{b['id']}", "budget_used", rng, langs, [money(b["spent_base"]), money(b["percent_used"])],
                          lambda l, n=b["name"]: {"budget": n}, category="budgets", level="complex")
    goals = rows(user, "Goal")
    for gid, name in (unique_names(goals) if goals is not None else {}).items():
        g = goals.get(pk=gid)
        left = dec(g.target_amount) - dec(g.current_saved_amount)
        if left > 0 and dec(g.target_amount) > 0:
            out += expand(f"goal_left:{gid}", "goal_left", rng, langs, [money(left)], lambda l, n=name: {"goal": n}, category="budgets")
    return out


def evaluate(user, langs, rng) -> list:
    out = []
    for b in _budgets(user):
        if nonzero([b["remaining_base"]]):
            out += expand(f"budget_left:{b['id']}", "budget_left", rng, langs, [money(b["remaining_base"])], lambda l, n=b["name"]: {"budget": n},
                          category="budgets", prefix="eval:")
    goals = rows(user, "Goal")
    for gid, name in (unique_names(goals) if goals is not None else {}).items():
        g = goals.get(pk=gid)
        share = percent(g.current_saved_amount, g.target_amount)
        if share and nonzero([share]) and dec(share) != 100:
            out += expand(f"goal_pct:{gid}", "goal_pct", rng, langs, [share], lambda l, n=name: {"goal": n}, category="budgets", level="complex", prefix="eval:")
    return out
