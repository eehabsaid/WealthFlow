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

    # Document (GenericForeignKey), LogEntry and Permission point at a ContentType: store
    # "app_label.model_name" instead of the raw integer content_type_id (ids differ between databases).
    if hasattr(instance, "content_type_id"):
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

    _add_natural_hints(row, field_map)
    return row


def _add_natural_hints(row: dict[str, Any], field_map: dict) -> None:
    """FKs to Permission / Group get a database-independent hint (ids differ between databases):
    __<fk>__perm = "app_label.model.codename", __<fk>__group = group name. Resolved by the restore."""
    from django.contrib.auth.models import Group, Permission

    for attname, field in field_map.items():
        if not (isinstance(field, (django_models.ForeignKey, django_models.OneToOneField)) and attname.endswith("_id")):
            continue
        value, base = row.get(attname), attname[:-3]
        if value is None:
            continue
        if field.related_model is Permission:
            perm = Permission.objects.select_related("content_type").filter(pk=value).first()
            row[f"__{base}__perm"] = f"{perm.content_type.app_label}.{perm.content_type.model}.{perm.codename}" if perm else None
        elif field.related_model is Group:
            group = Group.objects.filter(pk=value).first()
            row[f"__{base}__group"] = group.name if group else None


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
