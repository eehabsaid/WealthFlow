from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, Expense, RecurringTransaction
from core.services.budgets.recurring_service import RecurringService, _advance

User = get_user_model()


class AdvanceHelperTest(TestCase):
    def test_advance_monthly(self):
        # relativedelta clamps to the shorter month's last day (Feb 2026 has 28 days).
        self.assertEqual(_advance(date(2026, 1, 31), "monthly", 1), date(2026, 2, 28))

    def test_advance_weekly(self):
        self.assertEqual(_advance(date(2026, 1, 1), "weekly", 2), date(2026, 1, 15))

    def test_advance_daily(self):
        self.assertEqual(_advance(date(2026, 1, 1), "daily", 5), date(2026, 1, 6))

    def test_advance_yearly(self):
        self.assertEqual(_advance(date(2026, 1, 1), "yearly", 1), date(2027, 1, 1))


class RecurringServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="recurring_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        # Matching cash balance entry, required by ExpenseService.create_expense.
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.egp, amount=10000,
        )

    def test_create_recurring_sets_next_run_to_start_date(self):
        rec = RecurringService.create_recurring(
            {"name": "Netflix", "amount": 200, "currency_id": self.egp.id,
             "frequency": "monthly", "start_date": "2026-01-05", "backfill_missed": True},
            self.user,
        )
        self.assertEqual(rec.next_run_date, date(2026, 1, 5))
        self.assertTrue(rec.is_active)

    def test_process_due_posts_expense_and_advances_next_run_date(self):
        rec = RecurringTransaction.objects.create(
            owner=self.user, name="Netflix", amount=200, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 1, 5), next_run_date=date(2026, 1, 5),
        )
        created, skipped = RecurringService.process_due(self.user, as_of=date(2026, 1, 10))
        self.assertEqual(len(created), 1)
        self.assertEqual(skipped, [])
        rec.refresh_from_db()
        self.assertEqual(rec.next_run_date, date(2026, 2, 5))
        self.assertEqual(rec.last_run_date, date(2026, 1, 5))
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 1)

    def test_process_due_catches_up_multiple_missed_occurrences(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Rent", amount=100, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2025, 11, 1), next_run_date=date(2025, 11, 1),
        )
        created, skipped = RecurringService.process_due(self.user, as_of=date(2026, 2, 1))
        # Nov, Dec, Jan, Feb 1st occurrences are all due.
        self.assertEqual(len(created), 4)
        self.assertEqual(skipped, [])

    def test_process_due_leaves_inactive_recurring_alone(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Old gym", amount=100, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 1, 1), next_run_date=date(2026, 1, 1), is_active=False,
        )
        created, skipped = RecurringService.process_due(self.user, as_of=date(2026, 2, 1))
        self.assertEqual(created, [])
        self.assertEqual(skipped, [])

    def test_process_due_skips_and_retries_on_insufficient_balance(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Big bill", amount=999999, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 1, 1), next_run_date=date(2026, 1, 1),
        )
        created, skipped = RecurringService.process_due(self.user, as_of=date(2026, 2, 1))
        self.assertEqual(created, [])
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["reason"], "insufficient_balance")

    def test_process_due_deactivates_past_end_date(self):
        rec = RecurringTransaction.objects.create(
            owner=self.user, name="Trial", amount=50, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 1, 1), next_run_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
        )
        RecurringService.process_due(self.user, as_of=date(2026, 3, 1))
        rec.refresh_from_db()
        self.assertFalse(rec.is_active)


class RecurringNoBackfillByDefaultTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nobackfill_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.egp, amount=100000,
        )

    def test_past_start_date_does_not_backfill_by_default(self):
        today = date.today()
        start = today.replace(year=today.year - 1)
        rec = RecurringService.create_recurring(
            {"name": "Gym", "amount": 100, "currency_id": self.egp.id,
             "frequency": "monthly", "start_date": start.isoformat()},
            self.user,
        )
        self.assertGreaterEqual(rec.next_run_date, today)
        created, skipped = RecurringService.process_due(self.user)
        self.assertLessEqual(len(created), 1)  # at most today's occurrence, never history

    def test_backfill_opt_in_keeps_start_date(self):
        rec = RecurringService.create_recurring(
            {"name": "Old", "amount": 10, "currency_id": self.egp.id, "frequency": "monthly",
             "start_date": "2026-01-01", "backfill_missed": True},
            self.user,
        )
        self.assertEqual(rec.next_run_date, date(2026, 1, 1))

    def test_future_start_date_is_unchanged(self):
        future = date.today().replace(year=date.today().year + 1)
        rec = RecurringService.create_recurring(
            {"name": "Future", "amount": 10, "currency_id": self.egp.id, "frequency": "monthly",
             "start_date": future.isoformat()},
            self.user,
        )
        self.assertEqual(rec.next_run_date, future)

    def test_preview_due_writes_nothing_and_matches_process_due(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Rent", amount=100, currency=self.egp, payment_method="Cash",
            frequency="monthly", interval=1, start_date=date(2025, 11, 1), next_run_date=date(2025, 11, 1),
        )
        as_of = date(2026, 2, 1)
        preview = RecurringService.preview_due(self.user, as_of=as_of)
        self.assertEqual(len(preview), 4)
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 0)
        self.assertEqual(RecurringTransaction.objects.get(owner=self.user).next_run_date, date(2025, 11, 1))
        created, _ = RecurringService.process_due(self.user, as_of=as_of)
        self.assertEqual(len(created), len(preview))

    def test_preview_ignores_inactive_items(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Paused", amount=100, currency=self.egp, payment_method="Cash",
            frequency="monthly", interval=1, start_date=date(2026, 1, 1), next_run_date=date(2026, 1, 1),
            is_active=False,
        )
        self.assertEqual(RecurringService.preview_due(self.user, as_of=date(2026, 6, 1)), [])
