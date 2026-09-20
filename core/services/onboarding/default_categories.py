"""Default expense categories every new user starts with."""

DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Groceries", "icon": "🛒", "color_hex": "#198754"},
    {"name": "Dining Out", "icon": "🍽️", "color_hex": "#fd7e14"},
    {"name": "Transport", "icon": "🚗", "color_hex": "#0d6efd"},
    {"name": "Housing & Rent", "icon": "🏠", "color_hex": "#6f42c1"},
    {"name": "Utilities & Bills", "icon": "💡", "color_hex": "#ffc107"},
    {"name": "Health", "icon": "🩺", "color_hex": "#dc3545"},
    {"name": "Education", "icon": "📚", "color_hex": "#20c997"},
    {"name": "Entertainment", "icon": "🎬", "color_hex": "#d63384"},
    {"name": "Shopping", "icon": "🛍️", "color_hex": "#0dcaf0"},
    {"name": "Other", "icon": "💰", "color_hex": "#6c757d"},
]


def seed_default_expense_categories(user):
    """Idempotent: creates only the defaults the user does not already have."""
    from core.models import ExpenseCategory

    created = 0
    for order, spec in enumerate(DEFAULT_EXPENSE_CATEGORIES, start=1):
        _, was_created = ExpenseCategory.objects.get_or_create(
            owner=user, name=spec["name"],
            defaults={"icon": spec["icon"], "color_hex": spec["color_hex"], "order": order},
        )
        created += int(was_created)
    return created
