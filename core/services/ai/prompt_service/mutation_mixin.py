"""
Write-side operations for AI Prompt Library: create, update, soft-delete,
favorite toggling, usage tracking, and duplication.
"""

from django.utils import timezone

from core.models.ai_prompt import AIPrompt
from core.services.ai.prompt_serializer import serialize_prompt


class PromptMutationMixin:
    @staticmethod
    def create_prompt(data, user=None):
        from core.services.ai.prompt_service import AIPromptService

        is_valid, errors, category = AIPromptService.validate_prompt_data(data)
        if not is_valid:
            return False, errors, None

        name = str(data.get("name", "")).strip()
        content = str(data.get("content", "")).strip()
        description = str(data.get("description", "") or "").strip()
        is_favorite = bool(data.get("is_favorite", False))
        display_order = int(data.get("display_order", 0) or 0)

        prompt = AIPrompt.objects.create(
            user=user if (user and user.is_authenticated) else None,
            name=name,
            content=content,
            category=category,
            description=description,
            is_favorite=is_favorite,
            is_active=True,
            display_order=display_order,
        )
        return True, None, serialize_prompt(prompt)

    @staticmethod
    def update_prompt(prompt_id, data):
        from core.services.ai.prompt_service import AIPromptService

        prompt = AIPrompt.objects.filter(id=prompt_id, is_active=True).first()
        if not prompt:
            return False, {"error": "Prompt not found."}, None

        is_valid, errors, category = AIPromptService.validate_prompt_data(data, instance_id=prompt_id)
        if not is_valid:
            return False, errors, None

        if "name" in data:
            prompt.name = str(data["name"]).strip()
        if "content" in data:
            prompt.content = str(data["content"]).strip()
        if category:
            prompt.category = category
        if "description" in data:
            prompt.description = str(data["description"] or "").strip()
        if "is_favorite" in data:
            prompt.is_favorite = bool(data["is_favorite"])
        if "display_order" in data:
            try:
                prompt.display_order = int(data["display_order"])
            except (ValueError, TypeError):
                pass

        prompt.save()
        return True, None, serialize_prompt(prompt)

    @staticmethod
    def delete_prompt(prompt_id):
        """
        Soft-delete prompt by setting is_active=False.
        """
        prompt = AIPrompt.objects.filter(id=prompt_id, is_active=True).first()
        if not prompt:
            return False, "Prompt not found."

        prompt.is_active = False
        prompt.save()
        return True, None

    @staticmethod
    def toggle_favorite(prompt_id):
        prompt = AIPrompt.objects.filter(id=prompt_id, is_active=True).first()
        if not prompt:
            return False, "Prompt not found.", None

        prompt.is_favorite = not prompt.is_favorite
        prompt.save()
        return True, None, serialize_prompt(prompt)

    @staticmethod
    def record_usage(prompt_id):
        prompt = AIPrompt.objects.filter(id=prompt_id, is_active=True).first()
        if not prompt:
            return False, "Prompt not found.", None

        prompt.usage_count += 1
        prompt.last_used_at = timezone.now()
        prompt.save(update_fields=["usage_count", "last_used_at", "updated_at"])
        return True, None, serialize_prompt(prompt)

    @staticmethod
    def duplicate_prompt(prompt_id):
        source = AIPrompt.objects.filter(id=prompt_id, is_active=True).first()
        if not source:
            return False, "Source prompt not found.", None

        base_name = source.name
        copy_suffix = " (Copy)"
        new_name = f"{base_name}{copy_suffix}"
        counter = 1

        while AIPrompt.objects.filter(is_active=True, name__iexact=new_name).exists():
            counter += 1
            new_name = f"{base_name}{copy_suffix} {counter}"

        new_prompt = AIPrompt.objects.create(
            user=source.user,
            name=new_name,
            content=source.content,
            category=source.category,
            description=source.description,
            is_favorite=source.is_favorite,
            is_active=True,
            display_order=source.display_order + 1,
        )
        return True, None, serialize_prompt(new_prompt)
