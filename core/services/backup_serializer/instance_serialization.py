"""Model-instance serialization helpers used by the backup_data command.

Pure code motion from the original backup_data.py management command —
same logic, same order of operations, only relocated so that backup_data.py
can stay a flat, Django-discoverable command module under 200 lines.
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.db import models as django_models
from django.contrib.contenttypes.models import ContentType

from core.services.backup_serializer.value_conversion import serialize_value
from core.services.backup_serializer.content_type import content_type_label


def get_field_map(model_class) -> dict[str, django_models.Field]:
    """Return {field.attname: field} for all concrete fields on a model."""
    return {f.attname: f for f in model_class._meta.get_fields()
            if isinstance(f, django_models.Field) and not f.many_to_many and getattr(f, "concrete", True)}


def serialize_instance(instance, field_map: dict) -> dict[str, Any]:
    """
    Serialise one model instance to a plain dict.
    All values are JSON-safe primitives.
    """
    row: dict[str, Any] = {}
    for attname, field in field_map.items():
        raw = getattr(instance, attname, None)
        row[attname] = serialize_value(raw)

    # Special handling: Document uses GenericForeignKey via ContentType.
    # Store "app_label.model_name" instead of the raw integer content_type_id.
    if hasattr(instance, "content_type_id") and hasattr(instance, "object_id"):
        try:
            ct = ContentType.objects.get(pk=instance.content_type_id)
            row["_content_type_label"] = content_type_label(ct)
        except ContentType.DoesNotExist:
            row["_content_type_label"] = None

    # Store username for any field that is a FK to auth.User so that restore
    # can match by username rather than raw integer PK.
    from django.contrib.auth.models import User
    for attname, field in field_map.items():
        if (isinstance(field, (django_models.ForeignKey, django_models.OneToOneField))
                and field.related_model is User
                and attname.endswith("_id")):
            user_id = row.get(attname)
            if user_id is not None:
                try:
                    row[f"__{attname[:-3]}__username"] = (
                        User.objects.get(pk=user_id).username
                    )
                except User.DoesNotExist:
                    row[f"__{attname[:-3]}__username"] = None

    return row


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_last_migration() -> str:
    """Return the name of the last applied migration."""
    try:
        from django.db.migrations.recorder import MigrationRecorder
        last = (
            MigrationRecorder.Migration.objects
            .order_by("-applied")
            .values_list("app", "name")
            .first()
        )
        return f"{last[0]}.{last[1]}" if last else "none"
    except Exception:
        return "unknown"
