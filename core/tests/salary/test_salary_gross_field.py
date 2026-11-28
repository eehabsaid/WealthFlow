"""SalaryEntry.gross: to_dict, backup serialization, API create/update (test DB)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Company, SalaryEntry
from core.services.backup_serializer import get_field_map, serialize_instance


class SalaryGrossFieldTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gross_owner", password="pw123456")
        self.co = Company.objects.create(owner=self.user, name="Acme", display_name="Acme")
        self.client.force_login(self.user)

    def test_to_dict_includes_gross(self):
        e = SalaryEntry.objects.create(
            company=self.co, year=2026, month="January", paid=Decimal("11000"),
            expected=Decimal("11000"), bonus=Decimal("0"), gross=Decimal("13000"),
        )
        d = e.to_dict()
        self.assertEqual(d["gross"], 13000.0)
        e.gross = None
        e.save()
        self.assertIsNone(SalaryEntry.objects.get(id=e.id).to_dict()["gross"])

    def test_backup_serialization_includes_gross(self):
        e = SalaryEntry.objects.create(
            company=self.co, year=2026, month="February", paid=Decimal("12000"),
            expected=Decimal("12000"), bonus=Decimal("0"), gross=Decimal("14000"),
        )
        row = serialize_instance(e, get_field_map(SalaryEntry))
        self.assertEqual(Decimal(str(row["gross"])), Decimal("14000"))
        e.gross = None
        e.save()
        row2 = serialize_instance(e, get_field_map(SalaryEntry))
        self.assertIsNone(row2["gross"])

    def test_api_create_and_update_gross(self):
        r = self.client.post("/api/salary/", {
            "company_id": self.co.id, "year": 2026, "month": "March",
            "expected": 10000, "paid": 9000, "bonus": 0, "gross": 11500,
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        eid = r.json()["id"]
        self.assertEqual(SalaryEntry.objects.get(id=eid).gross, Decimal("11500"))

        r2 = self.client.put(f"/api/salary/{eid}/", {"gross": 12000}, content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(SalaryEntry.objects.get(id=eid).gross, Decimal("12000"))

        r3 = self.client.put(f"/api/salary/{eid}/", {"gross": ""}, content_type="application/json")
        self.assertEqual(r3.status_code, 200)
        self.assertIsNone(SalaryEntry.objects.get(id=eid).gross)
