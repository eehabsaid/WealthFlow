"""Commitments calendar certificate events must match CashFlowForecastService exactly."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Bank, BankCertificate, BankCertificateInterestHistory, Currency

from .commitments_calendar_helpers import calendar_events, calendar_view, forecast_view

User = get_user_model()


class CertificateParityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_cert", password="x12345678")
        self.bank = Bank.objects.create(owner=self.user, name="Cert Bank")
        self.egp = Currency.objects.create(code="EGP", symbol="E", name="Egyptian Pound")
        BalanceEntry.objects.create(owner=self.user, title="cash", balance_type=BalanceEntry.BalanceType.CASH,
                                    currency=self.egp, amount=50000000, bank=self.bank)

    def cert(self, issue, expiry, frequency, interest, amount=100000, **extra):
        return BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.egp, amount=amount, interest_value=interest,
            issue_date=issue, expiry_date=expiry, frequency=frequency, **{"status": "active", **extra})

    def check(self, expected):
        """Assert the calendar events and that they equal the forecast's own certificate events."""
        events = calendar_events(self.user)
        self.assertEqual([(e["date"], e["event_type"], e["amount"]) for e in events], expected)
        self.assertEqual(calendar_view(events), forecast_view(self.user))
        return events

    def test_monthly_with_maturity_on_an_interest_date(self):
        # 2027-02-10 is both the last interest date and the expiry: folded into maturity, not duplicated.
        self.cert(date(2026, 6, 10), date(2027, 2, 10), "monthly", 1000)
        self.check([("2026-12-10", "certificate_interest", 1000.0), ("2027-01-10", "certificate_interest", 1000.0),
                    ("2027-02-10", "certificate_maturity", 101000.0)])

    def test_quarterly_with_maturity_on_an_interest_date(self):
        self.cert(date(2026, 3, 5), date(2027, 9, 5), "quarterly", 3000)
        self.check([("2026-12-05", "certificate_interest", 3000.0), ("2027-03-05", "certificate_interest", 3000.0),
                    ("2027-06-05", "certificate_interest", 3000.0), ("2027-09-05", "certificate_maturity", 103000.0)])

    def test_yearly_matures_after_the_range_so_only_interest_inside_it_shows(self):
        self.cert(date(2025, 12, 20), date(2028, 12, 20), "yearly", 12000)
        self.check([("2026-12-20", "certificate_interest", 12000.0)])

    def test_maturity_not_on_an_interest_date_carries_principal_only(self):
        self.cert(date(2026, 6, 10), date(2027, 1, 25), "monthly", 1000)
        events = self.check([("2026-12-10", "certificate_interest", 1000.0), ("2027-01-10", "certificate_interest", 1000.0),
                             ("2027-01-25", "certificate_maturity", 100000.0)])
        self.assertEqual(events[-1]["extra"], {"principal": 100000.0, "interest": 0.0})

    def test_interest_already_posted_is_excluded(self):
        self.cert(date(2026, 6, 10), date(2027, 2, 10), "monthly", 1000, last_interest_posted_date=date(2026, 12, 10))
        self.check([("2027-01-10", "certificate_interest", 1000.0), ("2027-02-10", "certificate_maturity", 101000.0)])

    def test_posted_interest_up_to_the_maturity_date_is_not_added_to_maturity(self):
        self.cert(date(2026, 6, 10), date(2027, 2, 10), "monthly", 1000, last_interest_posted_date=date(2027, 2, 10))
        self.check([("2027-02-10", "certificate_maturity", 100000.0)])

    def test_history_rows_are_honoured_like_the_forecast(self):
        cert = self.cert(date(2026, 6, 10), date(2027, 2, 10), "monthly", 1000)
        BankCertificateInterestHistory.objects.create(certificate=cert, posting_date=date(2026, 11, 10),
                                                      posting_period="monthly:2026-11-10", interest_amount=1000)
        self.check([("2026-12-10", "certificate_interest", 1000.0), ("2027-01-10", "certificate_interest", 1000.0),
                    ("2027-02-10", "certificate_maturity", 101000.0)])

    def test_expired_and_inactive_certificates_produce_nothing(self):
        self.cert(date(2025, 1, 10), date(2026, 10, 1), "monthly", 1000)  # expired
        self.cert(date(2025, 11, 22), date(2026, 11, 22), "monthly", 1000)  # expires today: already due
        self.cert(date(2026, 6, 10), date(2027, 6, 10), "monthly", 1000, status="closed")  # inactive
        self.check([])

    def test_event_is_attributed_to_its_certificate_and_bank(self):
        cert = self.cert(date(2026, 6, 10), date(2027, 1, 25), "monthly", 1000)
        for e in calendar_events(self.user):
            self.assertEqual((e["source"], e["source_id"], e["bank_id"]), ("BankCertificate", cert.id, self.bank.id))
