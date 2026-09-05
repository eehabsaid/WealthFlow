"""
Input validation for AI Prompt Library create/update requests.
"""

from core.models.ai_prompt import AIPrompt, AIPromptCategory


class PromptValidationMixin:
    @staticmethod
    def validate_prompt_data(data, instance_id=None):
        errors = {}
        name = str(data.get("name", "") or "").strip()
        content = str(data.get("content", "") or "").strip()
        category_id = data.get("category_id")
        category_code = str(data.get("category_code", "") or "").strip()

        if not name:
            errors["name"] = "Prompt name is required."
        elif len(name) > 255:
            errors["name"] = "Prompt name must not exceed 255 characters."
        else:
            # Check duplicate name among ACTIVE prompts
            qs = AIPrompt.objects.filter(is_active=True, name__iexact=name)
            if instance_id:
                qs = qs.exclude(id=instance_id)
            if qs.exists():
                errors["name"] = f"An active prompt with the name '{name}' already exists."

        if not content:
            errors["content"] = "Prompt content is required."
        elif len(content) > 10000:
            errors["content"] = "Prompt content must not exceed 10000 characters."

        category = None
        if category_id:
            category = AIPromptCategory.objects.filter(id=category_id, is_active=True).first()
        elif category_code:
            category = AIPromptCategory.objects.filter(code=category_code, is_active=True).first()

        if not category:
            # Fallback to default category if exists, else error
            category = AIPromptCategory.objects.filter(code="general", is_active=True).first()
            if not category:
                category = AIPromptCategory.objects.filter(is_active=True).first()
            if not category:
                errors["category"] = "Valid prompt category is required."

        return len(errors) == 0, errors, category
