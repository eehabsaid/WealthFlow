import math
from django.db.models import Q
from django.utils import timezone
from core.models.ai_prompt import AIPrompt, AIPromptCategory
from core.services.ai.prompt_serializer import serialize_prompt, serialize_prompt_category


class AIPromptService:
    """
    Service layer providing business logic for AI Workspace Prompt Library.
    """

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

    @staticmethod
    def get_prompts(
        user=None,
        category_id=None,
        category_code=None,
        search_query=None,
        favorites_only=False,
        sort_by="favorites",
        page=1,
        page_size=20,
    ):
        qs = AIPrompt.objects.filter(is_active=True).select_related("category")

        if category_id:
            qs = qs.filter(category_id=category_id)
        elif category_code and category_code != "all":
            qs = qs.filter(category__code=category_code)

        if favorites_only:
            qs = qs.filter(is_favorite=True)

        if search_query:
            q = str(search_query).strip()
            if q:
                qs = qs.filter(
                    Q(name__icontains=q)
                    | Q(description__icontains=q)
                    | Q(content__icontains=q)
                    | Q(category__name__icontains=q)
                    | Q(category__code__icontains=q)
                )

        if sort_by == "recently_used":
            qs = qs.order_by("-last_used_at", "-updated_at", "name")
        elif sort_by == "most_used":
            qs = qs.order_by("-usage_count", "-updated_at", "name")
        elif sort_by == "name":
            qs = qs.order_by("name")
        elif sort_by == "updated":
            qs = qs.order_by("-updated_at")
        else:
            # Default: favorites first, then display_order, then updated_at desc
            qs = qs.order_by("-is_favorite", "display_order", "-updated_at", "name")

        total = qs.count()
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = int(page_size)
            if page_size < 1:
                page_size = 20
            elif page_size > 100:
                page_size = 100
        except (ValueError, TypeError):
            page_size = 20

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs[start:end])

        return {
            "items": [serialize_prompt(p) for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    def get_prompt_by_id(prompt_id):
        prompt = AIPrompt.objects.filter(id=prompt_id, is_active=True).select_related("category").first()
        if not prompt:
            return None
        return serialize_prompt(prompt)

    @staticmethod
    def create_prompt(data, user=None):
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

    @staticmethod
    def get_categories():
        categories = AIPromptCategory.objects.filter(is_active=True).order_by("display_order", "name")
        return [serialize_prompt_category(c) for c in categories]
