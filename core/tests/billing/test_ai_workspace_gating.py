from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import Plan, Subscription

User = get_user_model()

AI_ENDPOINTS = [
    "/api/financial-advisor/ai/chat/",
    "/api/financial-advisor/ai/conversations/",
    "/api/financial-advisor/ai/progress/",
    "/api/ai-platform/knowledge/",
    "/api/ai-platform/datasets/",
    "/api/ai-platform/models/",
    "/api/ai-platform/benchmarks/",
    "/api/ai-platform/prompts/",
]


class AIWorkspaceGatingTestCase(TestCase):
    def setUp(self):
        self.basic = Plan.objects.create(code="gt_basic", name="Gate Basic", sort_order=0, allows_ai_workspace=False)
        self.pro = Plan.objects.create(code="gt_pro", name="Gate Pro", sort_order=1, allows_ai_workspace=True)

    def _subscribe(self, user, plan):
        return Subscription.objects.create(
            owner=user,
            plan=plan,
            status="active",
            current_period_end=timezone.now() + timezone.timedelta(days=30),
        )

    def test_basic_plan_blocked_from_ai_endpoints(self):
        user = User.objects.create_user(username="basic_user", password="pass12345")
        self._subscribe(user, self.basic)
        self.client.force_login(user)

        for url in AI_ENDPOINTS:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 402)
                self.assertEqual(res.json().get("error"), "plan_upgrade_required")
                self.assertEqual(res.json().get("required_feature"), "allows_ai_workspace")

    def test_pro_plan_passes_the_gate(self):
        user = User.objects.create_user(username="pro_user", password="pass12345")
        self._subscribe(user, self.pro)
        self.client.force_login(user)

        for url in AI_ENDPOINTS:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertNotEqual(res.status_code, 402)

    def test_superuser_bypasses_the_gate_without_a_subscription(self):
        admin = User.objects.create_superuser(username="ai_admin", password="pass12345", email="a@a.com")
        self.client.force_login(admin)
        res = self.client.get("/api/financial-advisor/ai/chat/")
        self.assertNotEqual(res.status_code, 402)

    def test_no_subscription_blocked_from_ai_endpoints(self):
        user = User.objects.create_user(username="no_sub_user", password="pass12345")
        self.client.force_login(user)
        res = self.client.get("/api/financial-advisor/ai/chat/")
        self.assertEqual(res.status_code, 402)

    def test_expired_subscription_blocked_even_on_pro_plan(self):
        user = User.objects.create_user(username="expired_pro_user", password="pass12345")
        Subscription.objects.create(owner=user, plan=self.pro, status="expired")
        self.client.force_login(user)
        res = self.client.get("/api/financial-advisor/ai/chat/")
        self.assertEqual(res.status_code, 402)
