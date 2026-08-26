from core.services.shared.auth_workflow_service import AuthWorkflowService
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Expense, ExpenseCategory
from core.services.financial_advisor.opportunity_detection_service import OpportunityDetectionService

User = get_user_model()


class OpportunityDetectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="oppuser",
            email="oppuser@example.com",
            password="SecurePass123!",
            is_active=True
        )
        profile = AuthWorkflowService.get_profile(self.user)
        profile.email_verified = True
        profile.account_status = "active"
        profile.save()

    def test_opportunity_detection_service_payload(self):
        service = OpportunityDetectionService(today=date(2026, 7, 22))
        payload = service.payload()
        self.assertIn("as_of", payload)
        self.assertIn("opportunities", payload)
        self.assertIn("count", payload)
        self.assertEqual(payload["count"], len(payload["opportunities"]))

    def test_opportunity_detection_view_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/financial-advisor/opportunity-detection/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)

    def test_opportunity_detection_view_unauthenticated(self):
        response = self.client.get("/api/financial-advisor/opportunity-detection/")
        self.assertEqual(response.status_code, 401)


class SpendingIntelligenceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="spending_user", password="password123")
        self.cat1 = ExpenseCategory.objects.create(name="Food & Dining", icon="🍽️", color_hex="#fd7e14", order=1)
        self.cat2 = ExpenseCategory.objects.create(name="Utilities", icon="💡", color_hex="#0d6efd", order=2)
        
        # Create expenses across months and categories
        Expense.objects.create(
            date=date(2026, 6, 10),
            year=2026,
            month=6,
            category=self.cat1,
            amount=Decimal("500.00"),
            amount_egp=Decimal("500.00")
        )
        Expense.objects.create(
            date=date(2026, 6, 15),
            year=2026,
            month=6,
            category=self.cat2,
            amount=Decimal("300.00"),
            amount_egp=Decimal("300.00")
        )
        Expense.objects.create(
            date=date(2026, 7, 5),
            year=2026,
            month=7,
            category=self.cat1,
            amount=Decimal("800.00"),
            amount_egp=Decimal("800.00")
        )

    def test_spending_intelligence_registered_categories_and_by_category(self):
        from core.services.financial_advisor.spending_intelligence_service import SpendingIntelligenceService

        payload = SpendingIntelligenceService(today=date(2026, 7, 26)).payload()

        # Check registered categories
        reg_cats = payload.get("registered_categories", [])
        cat_names = [c["name"] for c in reg_cats]
        self.assertIn("Food & Dining", cat_names)
        self.assertIn("Utilities", cat_names)

        # Check monthly comparison by category
        monthly_comp = payload.get("monthly_comparison", {})
        by_category = monthly_comp.get("by_category", {})

        cat1_key = str(self.cat1.id)
        cat2_key = str(self.cat2.id)

        self.assertIn(cat1_key, by_category)
        self.assertIn(cat2_key, by_category)

        # cat1 has expenses in Jun (500) and Jul (800)
        cat1_months = by_category[cat1_key]
        self.assertEqual(len(cat1_months), 2)
        jun_cat1 = next(m for m in cat1_months if m["month"] == 6)
        self.assertEqual(jun_cat1["total_egp"], 500.0)

    def test_spending_intelligence_view(self):
        self.client.login(username="spending_user", password="password123")
        response = self.client.get("/api/financial-advisor/spending-intelligence/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("registered_categories", data)
        self.assertIn("by_category", data["monthly_comparison"])
