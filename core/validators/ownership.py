"""Row-level ownership helpers for per-user data isolation.

Root models (Bank, Company, FixedAsset, ExpenseCategory, Expense, Goal,
Scenario, ReminderRule, BankCertificate, BalanceEntry, BalanceTransfer,
CreditCardPayment, CardRenewalFee, BankInterest, CurrencyExchange) carry
their own `owner` FK (CurrencyExchange reuses its existing `user` field).
Child models (AssetPhoto, RealEstateDetails, ScenarioEvent, SalaryEntry,
etc.) have no `owner` field of their own — ownership is inherited through
their FK to a root model, so callers pass the relation name to walk
(e.g. parent_field="asset" for anything hanging off FixedAsset).

No caller gets a staff/superuser bypass here — ownership isolation is
absolute regardless of role, by design.
"""

from django.shortcuts import get_object_or_404


def _owned_queryset(model, request):
    """Queryset of `model` restricted to rows owned by request.user."""
    return model.objects.filter(owner=request.user)


def _owned_object_or_404(model, pk, request, **extra):
    """Single `model` row by pk, 404s if it isn't owned by request.user."""
    return get_object_or_404(model, pk=pk, owner=request.user, **extra)


def _child_owned_queryset(model, request, parent_field="asset"):
    """Queryset of a child `model` whose ownership is inherited through
    its FK named `parent_field` (e.g. AssetPhoto -> asset -> owner)."""
    lookup = f"{parent_field}__owner"
    return model.objects.filter(**{lookup: request.user})


def _child_owned_object_or_404(model, pk, request, parent_field="asset", **extra):
    lookup = f"{parent_field}__owner"
    return get_object_or_404(model, pk=pk, **{lookup: request.user}, **extra)
