from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return None


def serialize_prompt_category(category):
    if not category:
        return None
    return {
        "id": category.id,
        "code": category.code,
        "name": category.name,
        "description": category.description,
        "icon": category.icon,
        "display_order": category.display_order,
        "is_active": category.is_active,
        "prompts_count": category.prompts.filter(is_active=True).count(),
        "created_at": _date_to_iso(category.created_at),
        "updated_at": _date_to_iso(category.updated_at),
    }


def serialize_prompt(prompt):
    if not prompt:
        return None
    cat_dict = serialize_prompt_category(prompt.category) if prompt.category else None
    return {
        "id": prompt.id,
        "name": prompt.name,
        "content": prompt.content,
        "category": cat_dict,
        "category_id": prompt.category_id,
        "category_code": prompt.category.code if prompt.category else "",
        "category_name": prompt.category.name if prompt.category else "",
        "description": prompt.description,
        "translation_key": prompt.translation_key,
        "is_favorite": prompt.is_favorite,

        "is_active": prompt.is_active,
        "display_order": prompt.display_order,
        "usage_count": prompt.usage_count,
        "last_used_at": _date_to_iso(prompt.last_used_at),
        "created_at": _date_to_iso(prompt.created_at),
        "updated_at": _date_to_iso(prompt.updated_at),
    }
