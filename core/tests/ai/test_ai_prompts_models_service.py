"""
Unit tests for AI Prompt Library models, services, serializers, and REST API endpoints.
"""

from django.test import TestCase
from django.contrib.auth.models import User

from core.models.ai_prompt import AIPrompt, AIPromptCategory
from core.services.ai import AIPromptService, serialize_prompt, serialize_prompt_category

class AIPromptModelsServiceTest(TestCase):
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

    def test_prompt_serializers(self):
        cat_dict = serialize_prompt_category(self.cat_general)
        self.assertEqual(cat_dict["code"], "general")
        self.assertIn("prompts_count", cat_dict)

        prompt = AIPrompt.objects.create(
            name="Test Serializer Prompt",
            content="Sample content body.",
            category=self.cat_general,
            description="Sample description.",
            is_favorite=True,
        )
        p_dict = serialize_prompt(prompt)
        self.assertEqual(p_dict["id"], prompt.id)
        self.assertEqual(p_dict["name"], "Test Serializer Prompt")
        self.assertTrue(p_dict["is_favorite"])
        self.assertEqual(p_dict["category_code"], "general")

    def test_service_validation_and_creation(self):
        # Empty name
        ok, errors, _ = AIPromptService.create_prompt({"name": "", "content": "Valid content"})
        self.assertFalse(ok)
        self.assertIn("name", errors)

        # Empty content
        ok, errors, _ = AIPromptService.create_prompt({"name": "Valid Name", "content": "   "})
        self.assertFalse(ok)
        self.assertIn("content", errors)

        # Successful creation
        ok, errors, p_dict = AIPromptService.create_prompt(
            {
                "name": "Unique Prompt 101",
                "content": "Analyze my salary and expenses.",
                "category_code": "general",
                "description": "Custom prompt description",
                "is_favorite": True,
            },
            user=self.user,
        )
        self.assertTrue(ok)
        self.assertEqual(p_dict["name"], "Unique Prompt 101")
        self.assertTrue(p_dict["is_favorite"])

        # Duplicate active name check
        ok2, errors2, _ = AIPromptService.create_prompt(
            {"name": "unique prompt 101", "content": "Another content"}
        )
        self.assertFalse(ok2)
        self.assertIn("name", errors2)

    def test_service_search_filtering_and_pagination(self):
        res = AIPromptService.get_prompts(search_query="Portfolio", page=1, page_size=10)
        self.assertIsInstance(res.get("items"), list)
        self.assertIn("total", res)
        self.assertIn("page_size", res)

        # Filter by category
        res_cat = AIPromptService.get_prompts(category_code="general")
        for item in res_cat["items"]:
            self.assertEqual(item["category_code"], "general")

        # Filter by favorites
        res_fav = AIPromptService.get_prompts(favorites_only=True)
        for item in res_fav["items"]:
            self.assertTrue(item["is_favorite"])

    def test_soft_delete_and_scoped_duplicate(self):
        ok, _, p_dict = AIPromptService.create_prompt(
            {"name": "Temporary Prompt", "content": "Temp content", "category_code": "general"}
        )
        self.assertTrue(ok)
        prompt_id = p_dict["id"]

        # Soft delete
        del_ok, _ = AIPromptService.delete_prompt(prompt_id)
        self.assertTrue(del_ok)

        # Verify soft delete flag in DB
        db_prompt = AIPrompt.objects.get(id=prompt_id)
        self.assertFalse(db_prompt.is_active)

        # Verify not returned in get_prompts or get_prompt_by_id
        self.assertIsNone(AIPromptService.get_prompt_by_id(prompt_id))

        # Re-creating a prompt with the same name as the soft-deleted prompt SHOULD succeed (scoped uniqueness)
        ok_recreate, _, new_p_dict = AIPromptService.create_prompt(
            {"name": "Temporary Prompt", "content": "New active temp content", "category_code": "general"}
        )
        self.assertTrue(ok_recreate)
        self.assertNotEqual(new_p_dict["id"], prompt_id)
