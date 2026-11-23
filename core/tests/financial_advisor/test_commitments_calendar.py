from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

from core.models import (
    AssetInsurance,
    AssetRental,
    Bank,
    BankCertificate,
    Currency,
    Expense,
    ExpenseCategory,
    FixedAsset,
    RecurringTransaction,
    VehicleDetails,
)
from core.services.financial_advisor.commitments_calendar_service import (
    CommitmentsCalendarService,
    resolve_window_days,
)

TODAY = date(2026, 11, 22)


def make_asset(owner, name):
    return FixedAsset.objects.create(
        owner=owner, name=name, asset_type="Other Assets", purchase_date=date(2025, 1, 1)
    )


class CommitmentsCalendarServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_user", password="x12345678")
        self.other = User.objects.create_user(username="cc_other", password="x12345678")
        self.egp = Currency.objects.create(code="EGP", symbol="E", name="Egyptian Pound")
        self.bank = Bank.objects.create(owner=self.user, name="Test Bank")
        self.cat = ExpenseCategory.objects.create(owner=self.user, name="Utilities")
        self.asset = make_asset(self.user, "My Asset")

    def service(self):
        return CommitmentsCalendarService(self.user, today=TODAY)

    def range(self):
        return date(2026, 11, 1), date(2026, 12, 31)

    def test_recurring_events_are_expected_outflows(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Internet", category=self.cat, amount=500,
            currency=self.egp, frequency="monthly", interval=1,
            start_date=date(2026, 11, 5), next_run_date=date(2026, 11, 5), is_active=True,
        )
        p = self.service().payload(*self.range())
        evs = [e for e in p["events"] if e["event_type"] == "recurring"]
        self.assertTrue(evs)
        self.assertEqual(evs[0]["kind"], "expected")
        self.assertEqual(evs[0]["category"], "expense")
        self.assertEqual(evs[0]["amount"], 500)

    def test_certificate_interest_and_maturity_are_actual(self):
        from core.models import BalanceEntry

        BalanceEntry.objects.create(
            owner=self.user, title="Cert Bank", balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp, amount=100000, bank=self.bank,
        )
        BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.egp,
            issue_date=date(2026, 6, 1), expiry_date=date(2027, 6, 1),
            amount=100000, interest_rate=10, interest_value=5000, frequency="semi-annually",
        )
        p = self.service().payload(date(2026, 11, 1), date(2027, 7, 1))
        interest = [e for e in p["events"] if e["event_type"] == "certificate_interest"]
        maturity = [e for e in p["events"] if e["event_type"] == "certificate_maturity"]
        self.assertTrue(interest)
        self.assertEqual(maturity[0]["kind"], "actual")
        # interest due on the expiry date is folded into maturity (not a separate interest event)
        self.assertEqual(maturity[0]["amount"], 105000)
        self.assertEqual((maturity[0]["extra"]["principal"], maturity[0]["extra"]["interest"]), (100000.0, 5000.0))
        self.assertEqual([e["date"] for e in interest], ["2026-12-01"])

    def test_renewals_are_informational(self):
        AssetInsurance.objects.create(asset=self.asset, company="ACME", expiry_date=date(2026, 12, 10), premium=2000)
        car = make_asset(self.user, "My Car")
        VehicleDetails.objects.create(asset=car, plate_number="ABC-123", license_expiry_date=date(2026, 12, 20))
        room = make_asset(self.user, "My Room")
        AssetRental.objects.create(asset=room, monthly_rent=3000, contract_start=date(2026, 1, 1), contract_end=date(2026, 12, 31))
        p = self.service().payload(*self.range())
        by_type = {e["event_type"]: e for e in p["events"]}
        self.assertEqual(by_type["insurance_renewal"]["kind"], "informational")
        self.assertEqual(by_type["vehicle_license_renewal"]["kind"], "informational")
        self.assertEqual(by_type["rental_contract_expiry"]["kind"], "informational")

    def test_filters_category_and_bank(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Internet", category=self.cat, amount=500,
            currency=self.egp, frequency="monthly", interval=1,
            start_date=date(2026, 11, 5), next_run_date=date(2026, 11, 5), is_active=True, bank=self.bank,
        )
        p_inc = self.service().payload(*self.range(), category="income")
        self.assertTrue(all(e["category"] == "income" for e in p_inc["events"]))
        p_bank = self.service().payload(*self.range(), bank_id=self.bank.id)
        self.assertTrue(p_bank["events"])
        self.assertTrue(all(e["bank_id"] == self.bank.id for e in p_bank["events"]))

    def test_range_validation(self):
        with self.assertRaises(ValueError):
            self.service().payload(date(2026, 12, 1), date(2026, 11, 1))
        with self.assertRaises(ValueError):
            self.service().payload(date(2026, 1, 1), date(2027, 1, 3))

    def test_concentration_window_and_risk_reason(self):
        c2 = ExpenseCategory.objects.create(owner=self.user, name="Phone")
        RecurringTransaction.objects.create(
            owner=self.user, name="A", category=self.cat, amount=9000, currency=self.egp,
            frequency="monthly", interval=1, start_date=date(2026, 12, 1), next_run_date=date(2026, 12, 1), is_active=True,
        )
        RecurringTransaction.objects.create(
            owner=self.user, name="B", category=c2, amount=4000, currency=self.egp,
            frequency="monthly", interval=1, start_date=date(2026, 12, 10), next_run_date=date(2026, 12, 10), is_active=True,
        )
        p = self.service().payload(*self.range())
        self.assertTrue(p["analysis"]["concentration_windows"])
        self.assertTrue(any(r["key"] == "commitments_risk_concentration" for r in p["analysis"]["risk_reasons"]))

    def test_window_days_setting_clamped(self):
        from core.models import AppSettings

        AppSettings.set("commitments_concentration_window_days", "999", user=self.user)
        self.assertEqual(resolve_window_days(self.user), 90)
        AppSettings.set("commitments_concentration_window_days", "0", user=self.user)
        self.assertEqual(resolve_window_days(self.user), 1)
        AppSettings.set("commitments_concentration_window_days", "abc", user=self.user)
        self.assertEqual(resolve_window_days(self.user), 30)

    def test_read_only_no_posting(self):
        RecurringTransaction.objects.create(
            owner=self.user, name="Internet", category=self.cat, amount=500,
            currency=self.egp, frequency="monthly", interval=1,
            start_date=date(2026, 11, 5), next_run_date=date(2026, 11, 5), is_active=True,
        )
        before = Expense.objects.count()
        self.service().payload(*self.range())
        self.assertEqual(Expense.objects.count(), before)

    def test_tenant_isolation(self):
        AssetInsurance.objects.create(
            asset=make_asset(self.other, "Other Asset"), company="X",
            expiry_date=date(2026, 12, 1), premium=100,
        )
        p = self.service().payload(*self.range())
        self.assertFalse(any(e["source"] == "AssetInsurance" for e in p["events"]))


class CommitmentsCalendarApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_api", password="x12345678")
        self.client.login(username="cc_api", password="x12345678")

    def test_ok(self):
        r = self.client.get("/api/financial-advisor/commitments-calendar/", {"start_date": "2026-11-01", "end_date": "2026-12-31"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ("events", "analysis", "filters", "settings"):
            self.assertIn(key, data)

    def test_bad_dates(self):
        r = self.client.get("/api/financial-advisor/commitments-calendar/", {"start_date": "2026-12-01", "end_date": "2026-11-01"})
        self.assertEqual(r.status_code, 400)

    def test_bad_category(self):
        r = self.client.get("/api/financial-advisor/commitments-calendar/", {"start_date": "2026-11-01", "end_date": "2026-12-31", "category": "nope"})
        self.assertEqual(r.status_code, 400)

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get("/api/financial-advisor/commitments-calendar/", {"start_date": "2026-11-01", "end_date": "2026-12-31"})
        self.assertEqual(r.status_code, 401)
