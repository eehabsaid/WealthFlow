from __future__ import annotations

import datetime

from core.services.financial_advisor.overview_service.context import OverviewContext


def build_alerts(ctx: OverviewContext) -> None:
    """Phase 7: Aggregate dynamic Alerts list."""
    alerts = []

    # - Emergency fund
    if ctx.emergency_months >= 6.0:
        alerts.append({
            "severity": "success",
            "icon": "bi-check-circle-fill",
            "class": "alert-success-badge",
            "title_key": "overview_alert_emergency_fund_healthy_title",
            "title_fallback": "Emergency fund is healthy",
            "desc_key": "overview_alert_emergency_fund_healthy_desc",
            "desc_fallback": "You have {months} months of expenses saved.",
            "params": {"months": round(ctx.emergency_months, 1)},
            "target_tab": "cash-flow-forecast"
        })
    else:
        alerts.append({
            "severity": "warning",
            "icon": "bi-exclamation-triangle-fill",
            "class": "alert-warning-badge",
            "title_key": "overview_alert_emergency_fund_low_title",
            "title_fallback": "Emergency fund is low",
            "desc_key": "overview_alert_emergency_fund_low_desc",
            "desc_fallback": "You have only {months} months of expenses saved.",
            "params": {"months": round(ctx.emergency_months, 1)},
            "target_tab": "cash-flow-forecast"
        })

    # - Certificate maturity
    if ctx.nearest_maturity and ctx.nearest_maturity.get("days_left") is not None:
        days_left = ctx.nearest_maturity["days_left"]
        if days_left <= 30:
            alerts.append({
                "severity": "info",
                "icon": "bi-clock-fill",
                "class": "alert-info-badge",
                "title_key": "overview_alert_cert_maturing_title",
                "title_fallback": "Certificate matures in {days} days",
                "desc_key": "overview_alert_cert_maturing_desc",
                "desc_fallback": "A certificate for {amount} EGP will mature on {date}.",
                "params": {
                    "days": days_left,
                    "amount": float(ctx.nearest_maturity.get("amount", 0.0)),
                    "date": ctx.nearest_maturity.get("date", "")
                },
                "target_tab": "cash-flow-forecast"
            })

    # - Spending trend check
    if ctx.spending_increase > 5.0:
        alerts.append({
            "severity": "danger",
            "icon": "bi-exclamation-triangle-fill",
            "class": "alert-danger-badge",
            "title_key": "overview_alert_spending_increased_title",
            "title_fallback": "Spending increased",
            "desc_key": "overview_alert_spending_increased_desc",
            "desc_fallback": "Your spending is up {pct}% compared to average.",
            "params": {"pct": round(ctx.spending_increase, 1)},
            "target_tab": "cash-flow-forecast"
        })

    # - Mortgage installment due
    upcoming_mortgages = [e for e in ctx.cash_flow_payload.get("timeline", [])[0].get("events", []) if e.get("type") == "mortgage_payment"]
    if upcoming_mortgages:
        mortgage_event = upcoming_mortgages[0]
        alerts.append({
            "severity": "warning",
            "icon": "bi-credit-card-fill",
            "class": "alert-warning-badge",
            "title_key": "overview_alert_mortgage_due_title",
            "title_fallback": "Mortgage payment due soon",
            "desc_key": "overview_alert_mortgage_due_desc",
            "desc_fallback": "Amount: {amount} EGP. Due date: {date}.",
            "params": {
                "amount": float(mortgage_event.get("amount", 0.0)),
                "date": mortgage_event.get("date", "")
            },
            "target_tab": "cash-flow-forecast"
        })

    # - Insurance policy check
    alerts.append({
        "severity": "success",
        "icon": "bi-shield-fill-check",
        "class": "alert-success-badge",
        "title_key": "overview_alert_insurance_up_to_date_title",
        "title_fallback": "Insurance payments are up to date",
        "desc_key": "overview_alert_insurance_up_to_date_desc",
        "desc_fallback": "All your insurance policies are active.",
        "target_tab": "portfolio-optimizer"
    })

    # Sorting alerts automatically by severity, then by due date
    def _alert_sort_key(a):
        severity_map = {"danger": 3, "warning": 2, "info": 1, "success": 0}
        sev_val = severity_map.get(a.get("severity"), 0)

        date_str = ""
        if "params" in a and "date" in a["params"]:
            date_str = str(a["params"]["date"])

        if not date_str:
            date_val = datetime.date(9999, 12, 31)
        else:
            try:
                date_val = datetime.date.fromisoformat(date_str)
            except ValueError:
                date_val = datetime.date(9999, 12, 31)
        return (-sev_val, date_val)

    ctx.alerts_sorted = sorted(alerts, key=_alert_sort_key)
