"""'Export my data': every row the user owns, as one JSON-safe dict (same row format as the backup)."""

from __future__ import annotations

from django.utils import timezone

from core.services.account.scope import SECRET_FIELDS, classify, owned_queryset
from core.services.backup_serializer import get_field_map, get_model_export_order, serialize_instance

EXPORT_FORMAT = "wealthflow-user-export"
EXPORT_VERSION = 1


def _label(model) -> str:
    return f"{model._meta.app_label}.{model.__name__}"


def build_user_export(user) -> dict:
    tables: dict[str, list] = {}
    for _prefix, model, _natural in get_model_export_order():
        if classify(model) == "global":
            continue
        drop = SECRET_FIELDS.get(model.__name__, set())
        field_map = {k: v for k, v in get_field_map(model).items() if k not in drop}
        rows = [serialize_instance(obj, field_map) for obj in owned_queryset(model, user).order_by("pk").iterator()]
        if rows:
            tables[_label(model)] = rows
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": timezone.now().isoformat(),
        "username": user.username,
        "row_counts": {label: len(rows) for label, rows in tables.items()},
        "tables": tables,
    }
