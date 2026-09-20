"""Does this owner have any financial data at all?

Used by Portfolio Optimizer and Risk Analysis so a brand-new user gets an
explicit empty state instead of computed defaults (health score, "Cash",
"EGP", "12 months emergency fund", ...) that look like real data.
All checks are owner-scoped.
"""
from __future__ import annotations

from core.models import BalanceEntry, BankCertificate, Expense, FixedAsset, Goal, SalaryEntry


def has_portfolio_data(owner) -> bool:
    """Any balance, certificate or fixed asset."""
    return (
        BalanceEntry.objects.filter(owner=owner).exists()
        or BankCertificate.objects.filter(owner=owner).exists()
        or FixedAsset.objects.filter(owner=owner).exists()
    )


def has_risk_data(owner) -> bool:
    """Portfolio data, or any expense / salary / goal (risk also covers income and goals)."""
    return (
        has_portfolio_data(owner)
        or Expense.objects.filter(owner=owner).exists()
        or SalaryEntry.objects.filter(company__owner=owner).exists()
        or Goal.objects.filter(owner=owner).exists()
    )
