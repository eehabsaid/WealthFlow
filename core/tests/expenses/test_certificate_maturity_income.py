"""Regression tests: a bank certificate's income must survive its Active -> Closed
transition and be recognized in each month independently (maturity month included).

Scenario mirrors the real data: certificate issued 2023-11-12, matured 2026-11-12,
monthly interest 8,375.83, interest posted 2026-10-12 and 2026-11-12 (maturity).
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, BankCertificate, BankCertificateInterestHistory, Currency
from core.services.reports.income_summary_service import build_income_summary

User = get_user_model()
INTEREST = 8375.83


class CertificateMaturityIncomeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mat_user", password="pass12345")
        self.client.force_login(self.user)
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.currency, amount=1000000,
        )
        self.cert = BankCertificate.objects.create(
            owner=self.user, currency=self.currency,
            issue_date=date(2023, 11, 12), expiry_date=date(2026, 11, 12),
            amount=529000, interest_rate=19, interest_value=INTEREST,
            frequency="monthly", status="Active",
        )
        for posting in (date(2026, 9, 12), date(2026, 10, 12), date(2026, 11, 12)):
            BankCertificateInterestHistory.objects.create(
                certificate=self.cert, posting_date=posting,
                posting_period=f"monthly:{posting.isoformat()}",
                interest_amount=INTEREST, bank_id=self.cert.bank_id,
                currency_id=self.cert.currency_id,
            )

    def _month(self, year, month):
        return build_income_summary(self.user, year=year, month=month)

    def test_october_income_includes_certificates_monthly_interest(self):
        summary = self._month(2026, 10)
        self.assertEqual(summary["total_interest"], INTEREST)
        self.assertEqual(summary["total_income"], INTEREST)

    def test_november_maturity_month_includes_maturity_interest(self):
        summary = self._month(2026, 11)
        self.assertEqual(summary["total_interest"], INTEREST)
        self.assertEqual(summary["total_income"], INTEREST)

    def test_september_and_december_are_independent(self):
        self.assertEqual(self._month(2026, 9)["total_interest"], INTEREST)
        # December: the certificate matured 2026-11-12, so it contributes nothing.
        self.assertEqual(self._month(2026, 12)["total_interest"], 0.0)
        self.assertEqual(self._month(2026, 12)["total_income"], 0.0)

    def test_closing_the_certificate_never_erases_historical_income(self):
        self.cert.status = "Closed"
        self.cert.save(update_fields=["status", "updated_at"])
        self.assertEqual(self._month(2026, 10)["total_interest"], INTEREST)
        self.assertEqual(self._month(2026, 11)["total_interest"], INTEREST)
        self.assertEqual(self._month(2026, 9)["total_interest"], INTEREST)
        self.assertEqual(self._month(2026, 12)["total_interest"], 0.0)

    def test_no_duplicate_interest_recognition(self):
        self.cert.status = "Closed"
        self.cert.save(update_fields=["status", "updated_at"])
        # Each month recognizes exactly one posting; the two months together are
        # exactly the two real payments (Oct 12 + Nov 12), nothing more.
        october = self._month(2026, 10)["total_interest"]
        november = self._month(2026, 11)["total_interest"]
        self.assertEqual(october, INTEREST)
        self.assertEqual(november, INTEREST)
        self.assertEqual(october + november, 2 * INTEREST)
        # A range covering both months counts each posting exactly once.
        rng = build_income_summary(
            self.user, start=date(2026, 10, 1), end=date(2026, 11, 30)
        )
        self.assertEqual(rng["total_interest"], 2 * INTEREST)

    def test_yearly_counts_each_real_posting_once_after_closure(self):
        self.cert.status = "Closed"
        self.cert.save(update_fields=["status", "updated_at"])
        yearly = build_income_summary(self.user, year=2026)
        self.assertAlmostEqual(yearly["total_interest"], 3 * INTEREST, places=2)

    def test_inactive_certificate_without_history_contributes_zero(self):
        other = BankCertificate.objects.create(
            owner=self.user, currency=self.currency,
            issue_date=date(2026, 6, 1), expiry_date=date(2026, 12, 31),
            amount=1000, interest_value=200, status="Inactive",
        )
        summary = self._month(2026, 10)
        # Only the active certificate's interest; the Inactive one adds nothing.
        self.assertEqual(summary["total_interest"], INTEREST)
        self.assertIsNotNone(other)

    def test_pdf_report_matches_screen_for_maturity_month(self):
        from core.services.reports.report_service import ReportService

        self.cert.status = "Closed"
        self.cert.save(update_fields=["status", "updated_at"])
        screen = self._month(2026, 11)["total_income"]
        pdf = ReportService.get_period_income(self.user, rtype="monthly", year=2026, month=11)
        self.assertEqual(screen, INTEREST)
        self.assertEqual(pdf, screen)
