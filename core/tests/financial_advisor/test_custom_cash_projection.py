from datetime import date

from django.test import TestCase

from core.models import BalanceEntry, Currency
from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import (
    compute_custom_cash_projection,
)


class CustomCashProjectionTest(TestCase):
    def setUp(self):
        self.egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")

        BalanceEntry.objects.create(
            title="Home Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        BalanceEntry.objects.create(
            title="USD Wallet",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd,
            amount=100,
        )

    def test_egp_only_scope_excludes_other_currencies(self):
        result = compute_custom_cash_projection(
            today=date(2026, 1, 1),
            target_date=date(2026, 1, 31),
            exclude_event_types=[],
            currency_scope="egp_only",
        )
        # With no recurring salary/expenses set up, starting balance should be
        # exactly the EGP-only cash total (1000), unaffected by the USD wallet.
        self.assertEqual(result["starting_balance"], 1000.0)
        self.assertEqual(result["currency_scope"], "egp_only")

    def test_invalid_currency_scope_falls_back_to_egp_only(self):
        result = compute_custom_cash_projection(
            today=date(2026, 1, 1),
            target_date=date(2026, 1, 31),
            exclude_event_types=[],
            currency_scope="not_a_real_scope",
        )
        self.assertEqual(result["currency_scope"], "egp_only")

    def test_unknown_exclude_types_are_ignored_not_errored(self):
        result = compute_custom_cash_projection(
            today=date(2026, 1, 1),
            target_date=date(2026, 1, 31),
            exclude_event_types=["not_a_real_type", "salary"],
            currency_scope="egp_only",
        )
        self.assertEqual(result["excluded_event_types"], ["salary"])

    def test_no_events_beyond_target_date_are_included(self):
        result = compute_custom_cash_projection(
            today=date(2026, 1, 1),
            target_date=date(2026, 1, 5),
            exclude_event_types=[],
            currency_scope="egp_only",
        )
        for event in result["included_events"]:
            self.assertLessEqual(event["date"], "2026-01-05")
