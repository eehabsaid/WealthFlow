from __future__ import annotations

from .utils import _to_float


class OverridesMixin:
    """Applies caller-supplied overrides before delegating to series building."""

    def forecast_with_overrides(self, scenario: str, overrides: dict | None = None) -> dict:
        """Public wrapper for the What-If Simulator and Scenario Planner.

        Applies caller-supplied *overrides* to a shallow copy of the portfolio
        dict, then delegates to the unmodified ``_build_series()`` method.
        When *overrides* is None or empty the output is byte-identical to
        calling ``_build_series(portfolio, scenario)`` directly.

        Supported override keys
        -----------------------
        monthly_salary_scale : float
            Multiplier applied to base salary.
        monthly_expense_scale : float
            Multiplier applied to estimated monthly expenses.
        monthly_salary_delta : float
            Additive monthly salary delta (e.g. +5000 EGP or -2000 EGP).
        monthly_expense_delta : float
            Additive monthly expense delta (e.g. +4500 EGP for new mortgage/household).
        lump_sum_outflows : list[dict]
            List of lump-sum cash outflows, e.g. [{"month_index": 5, "amount": 1000000}].
        lump_sum_inflows : list[dict]
            List of lump-sum cash inflows, e.g. [{"month_index": 2, "amount": 500000}].
        gold_value : float
            Replaces ``portfolio["gold_value"]`` before projecting gold growth.
        certificate_reinvest : str
            ``"reinvest"`` (default) keeps certificate_value unchanged.
            ``"cashout"`` zeros the certificate_value.
        """
        portfolio = self._portfolio()

        if overrides:
            portfolio = dict(portfolio)  # shallow copy — never mutate original

            # ── Gold allocation target override ───────────────────────────────
            if "gold_value" in overrides:
                portfolio["gold_value"] = float(overrides["gold_value"])

            # ── Salary / expense scale and deltas ─────────────────────────────
            salary_scale = float(overrides.get("monthly_salary_scale", 1.0))
            expense_scale = float(overrides.get("monthly_expense_scale", 1.0))
            salary_delta_val = float(overrides.get("monthly_salary_delta", 0.0))
            expense_delta_val = float(overrides.get("monthly_expense_delta", 0.0))

            lump_outflows = overrides.get("lump_sum_outflows", [])
            lump_inflows = overrides.get("lump_sum_inflows", [])

            has_timeline_overrides = (
                salary_scale != 1.0
                or expense_scale != 1.0
                or salary_delta_val != 0.0
                or expense_delta_val != 0.0
                or bool(lump_outflows)
                or bool(lump_inflows)
            )

            if has_timeline_overrides:
                base_salary = portfolio.get("monthly_salary", 0.0)
                original_timeline = portfolio.get("cash_timeline", [])

                # ── Compute monthly deltas ──────────────────────────────────
                salary_delta_per_month = (base_salary * (salary_scale - 1.0)) + salary_delta_val

                if original_timeline:
                    # Estimate monthly expense from timeline events. Expense events
                    # carry negative amounts (outflows), so take the absolute value
                    # to get a positive monthly burn rate.
                    expense_per_month = 0.0
                    for month in original_timeline[:3]:
                        for ev in month.get("events", []):
                            if str(ev.get("type", "")).startswith("expense") or str(ev.get("type", "")) == "mortgage":
                                expense_per_month += abs(_to_float(ev.get("amount", 0)))
                    expense_per_month /= min(3, len(original_timeline[:3])) if original_timeline[:3] else 1
                else:
                    # No timeline events: fall back to the portfolio's baseline
                    # monthly expenses (from NetWorthService certificate forecast).
                    expense_per_month = _to_float(portfolio.get("monthly_expenses", 0.0))

                expense_delta_per_month = (expense_per_month * (expense_scale - 1.0)) + expense_delta_val

                if original_timeline:
                    cumulative_delta = 0.0
                    new_timeline = []
                    for idx, month in enumerate(original_timeline):
                        cumulative_delta += salary_delta_per_month - expense_delta_per_month
                        for out_item in lump_outflows:
                            m_idx = int(out_item.get("month_index", 0))
                            if m_idx == idx + 1:
                                cumulative_delta -= float(out_item.get("amount", 0.0))
                        for in_item in lump_inflows:
                            m_idx = int(in_item.get("month_index", 0))
                            if m_idx == idx + 1:
                                cumulative_delta += float(in_item.get("amount", 0.0))
                        new_month = dict(month)
                        original_ending = _to_float(month.get("ending_cash", 0.0))
                        new_month["ending_cash"] = round(original_ending + cumulative_delta, 2)
                        new_timeline.append(new_month)
                    portfolio["cash_timeline"] = new_timeline
                else:
                    # No cash timeline: the baseline series reads cash as 0 for
                    # every month (see SeriesBuilderMixin._month_end_cash), so the
                    # adjusted timeline must start from the same 0 baseline — not
                    # from current_cash — or the delta would be offset by the
                    # entire cash balance. The series builder maps month_index i
                    # to timeline[i], so timeline[i] must carry exactly i months
                    # of the net monthly delta, with lump sums landing in their
                    # own month (no fabricated events).
                    months_ahead = self.MONTHS_AHEAD
                    monthly_net = salary_delta_per_month - expense_delta_per_month
                    cumulative = 0.0
                    new_timeline = [{"ending_cash": 0.0, "events": []}]  # index 0 = baseline
                    for idx in range(1, months_ahead + 1):
                        cumulative += monthly_net
                        for out_item in lump_outflows:
                            if int(out_item.get("month_index", 0)) == idx:
                                cumulative -= float(out_item.get("amount", 0.0))
                        for in_item in lump_inflows:
                            if int(in_item.get("month_index", 0)) == idx:
                                cumulative += float(in_item.get("amount", 0.0))
                        new_timeline.append({"ending_cash": round(cumulative, 2), "events": []})
                    portfolio["cash_timeline"] = new_timeline

            # ── Certificate reinvestment choice ───────────────────────────────
            if overrides.get("certificate_reinvest") == "cashout":
                portfolio["certificate_value"] = 0.0

        return self._build_series(portfolio, scenario)
