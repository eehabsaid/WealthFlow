import json
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class PayrollAutomationTest(TestCase):
    def setUp(self):
        from core.models import Currency, Bank, Company
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", flag="🇺🇸")
        self.bank = Bank.objects.create(name="Chase Bank", account_number="1234", card_id="5678", swift_code="CHAS")
        self.company = Company.objects.create(
            name="Test Company",
            display_name="Test Company Disp",
            is_active=True,
            current_salary_amount=5000,
            current_salary_currency=self.currency,
            payment_day=25,
            default_bank=self.bank,
        )

    def test_company_to_dict_includes_payroll_fields(self):
        d = self.company.to_dict()
        self.assertEqual(d["current_salary_amount"], 5000.0)
        self.assertEqual(d["current_salary_currency"], "USD")
        self.assertEqual(d["default_bank"], "Chase Bank")

    def test_generate_current_salary_creates_entries(self):
        response = self.client.post("/api/salary/generate-current/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created"], 1)
        self.assertEqual(data["skipped"], 0)
        
        # Second run should skip
        response = self.client.post("/api/salary/generate-current/")
        self.assertEqual(response.json()["created"], 0)
        self.assertEqual(response.json()["skipped"], 1)

    def test_mark_salary_paid_and_reverse(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        self.assertEqual(entry.paid, 0)
        
        # Mark paid
        response = self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.paid, 5000.0)
        
        # Check bank balance
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))
        
        # Reverse payment
        response = self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": False}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.paid, 0)
        
        # Check bank balance reversed
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))

    def test_company_post_and_put_payroll_fields(self):
        # Test POST creation
        post_data = {
            "name": "New Company API",
            "display_name": "New Company API Disp",
            "group_name": "API Group",
            "color_hex": "#ff0000",
            "is_active": True,
            "order": 5,
            "current_salary_amount": 4200.0,
            "current_salary_currency_id": self.currency.id,
            "payment_day": 20,
            "default_bank_id": self.bank.id,
            "per_diem_amount": 150.0,
            "per_diem_currency_id": self.currency.id,
            "bonus_amount": 500.0,
            "payroll_notes": "Added via POST API",
        }
        response = self.client.post("/api/companies/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        new_company_id = res_data["id"]
        self.assertEqual(res_data["current_salary_amount"], 4200.0)
        self.assertEqual(res_data["payment_day"], 20)
        self.assertEqual(res_data["payroll_notes"], "Added via POST API")

        # Test PUT update
        put_data = {
            "current_salary_amount": 4800.0,
            "payment_day": 18,
            "payroll_notes": "Updated via PUT API",
        }
        response = self.client.put(f"/api/companies/{new_company_id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["current_salary_amount"], 4800.0)
        self.assertEqual(res_data["payment_day"], 18)
        self.assertEqual(res_data["payroll_notes"], "Updated via PUT API")

    def test_salary_paid_amount_update_adjusts_balance(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        
        # Mark paid
        self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))

        # Update paid from 5000 to 6000
        put_data = {
            "paid": 6000.0,
        }
        response = self.client.put(f"/api/salary/{entry.id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check bank balance adjusted by diff (+1000)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("6000.00"))

        # Update paid from 6000 to 4500
        put_data = {
            "paid": 4500.0,
        }
        response = self.client.put(f"/api/salary/{entry.id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check bank balance adjusted by diff (-1500)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("4500.00"))

    def test_salary_deletion_reverses_balance(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        
        # Mark paid (5000)
        self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))

        # Delete the entry
        response = self.client.delete(f"/api/salary/{entry.id}/")
        self.assertEqual(response.status_code, 200)

        # Check bank balance is fully reversed (5000 - 5000 = 0)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))
