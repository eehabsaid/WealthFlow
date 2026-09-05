"""
Read-side queries for AI Prompt Library: listing/search/pagination,
single-prompt lookup, and category listing.
"""

import math

from django.db.models import Q

from core.models.ai_prompt import AIPrompt, AIPromptCategory
from core.services.ai.prompt_serializer import serialize_prompt, serialize_prompt_category


class PromptQueryMixin:
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
    def get_categories():
        categories = AIPromptCategory.objects.filter(is_active=True).order_by("display_order", "name")
        return [serialize_prompt_category(c) for c in categories]
