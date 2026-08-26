"""
Unit tests for AI Prompt Library models, services, serializers, and REST API endpoints.
"""

from django.test import TestCase
from django.contrib.auth.models import User

from core.models.ai_prompt import AIPromptCategory
from core.services.ai import AIPromptService

class AIPromptApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_prompt_user", password="password123")

        self.cat_general = AIPromptCategory.objects.filter(code="general").first()
        if not self.cat_general:
            self.cat_general = AIPromptCategory.objects.create(
                code="general",
                name="General AI Directives",
                description="General prompts",
                icon="bi-chat-quote",
                display_order=1,
            )

        self.cat_finance = AIPromptCategory.objects.filter(code="financial_analysis").first()
        if not self.cat_finance:
            self.cat_finance = AIPromptCategory.objects.create(
                code="financial_analysis",
                name="Financial Analysis",
                description="Analysis prompts",
                icon="bi-graph-up",
                display_order=2,
            )

    def test_favorite_usage_and_duplication(self):
        ok, _, p_dict = AIPromptService.create_prompt(
            {"name": "Actionable Prompt", "content": "Content to duplicate", "category_code": "general"}
        )
        p_id = p_dict["id"]

        # Toggle favorite
        ok_fav, _, fav_p = AIPromptService.toggle_favorite(p_id)
        self.assertTrue(ok_fav)
        self.assertTrue(fav_p["is_favorite"])

        # Record usage
        ok_use, _, use_p = AIPromptService.record_usage(p_id)
        self.assertTrue(ok_use)
        self.assertEqual(use_p["usage_count"], 1)
        self.assertIsNotNone(use_p["last_used_at"])

        # Duplicate
        ok_dup, _, dup_p = AIPromptService.duplicate_prompt(p_id)
        self.assertTrue(ok_dup)
        self.assertEqual(dup_p["name"], "Actionable Prompt (Copy)")
        self.assertEqual(dup_p["content"], "Content to duplicate")

    def test_rest_api_endpoints(self):
        self.client.force_login(self.user)

        # List categories
        res_cat = self.client.get("/api/ai-platform/prompts/categories/")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn("categories", res_cat.json())

        # List prompts
        res_list = self.client.get("/api/ai-platform/prompts/")
        self.assertEqual(res_list.status_code, 200)
        self.assertIn("items", res_list.json())

        # Create via API
        payload = {
            "name": "API Test Prompt",
            "content": "Created via API request.",
            "category_code": "financial_analysis",
            "description": "API description",
        }
        res_create = self.client.post(
            "/api/ai-platform/prompts/",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.json()["prompt"]
        p_id = created_data["id"]

        # Detail GET
        res_detail = self.client.get(f"/api/ai-platform/prompts/{p_id}/")
        self.assertEqual(res_detail.status_code, 200)
        self.assertEqual(res_detail.json()["prompt"]["name"], "API Test Prompt")

        # Update PUT
        res_update = self.client.put(
            f"/api/ai-platform/prompts/{p_id}/",
            data={"name": "Updated API Test Prompt", "content": "Updated content."},
            content_type="application/json",
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["prompt"]["name"], "Updated API Test Prompt")

        # Favorite POST
        res_fav = self.client.post(f"/api/ai-platform/prompts/{p_id}/favorite/")
        self.assertEqual(res_fav.status_code, 200)

        # Use POST
        res_use = self.client.post(f"/api/ai-platform/prompts/{p_id}/use/")
        self.assertEqual(res_use.status_code, 200)

        # Duplicate POST
        res_dup = self.client.post(f"/api/ai-platform/prompts/{p_id}/duplicate/")
        self.assertEqual(res_dup.status_code, 201)

        # Delete DELETE
        res_del = self.client.delete(f"/api/ai-platform/prompts/{p_id}/")
        self.assertEqual(res_del.status_code, 200)
