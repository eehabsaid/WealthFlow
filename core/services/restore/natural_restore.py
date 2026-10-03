"""
Natural-key restore for tables whose primary keys are NOT portable between databases:
ContentType (app_label, model), Permission (content_type, codename) and the auto-created auth link
tables (user<->group, user<->permission, group<->permission).

Never sets or deletes a primary key: the pk-preserving path used by the other tables would delete a
Permission/ContentType that already holds that id and silently cascade through every link to it.
"""

from __future__ import annotations

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def uses_natural_restore(model_class) -> bool:
    return model_class in (ContentType, Permission) or bool(model_class._meta.auto_created)


def natural_restore_row(model_class, kwargs: dict, overwrite: bool) -> str:
    """Restore one row. Returns "created" | "updated" | "skipped"."""
    if model_class is ContentType:
        _, created = ContentType.objects.get_or_create(app_label=kwargs["app_label"], model=kwargs["model"])
        return "created" if created else "skipped"
    if model_class is Permission:
        if not kwargs.get("content_type_id"):   # its model no longer exists in this code base
            return "skipped"
        perm, created = Permission.objects.get_or_create(
            content_type_id=kwargs["content_type_id"], codename=kwargs["codename"], defaults={"name": kwargs.get("name") or kwargs["codename"]})
        if not created and overwrite and kwargs.get("name") and perm.name != kwargs["name"]:
            perm.name = kwargs["name"]
            perm.save(update_fields=["name"])
            return "updated"
        return "created" if created else "skipped"
    # auto-created link table: identity is the pair of foreign keys
    fks = {f.attname: kwargs.get(f.attname) for f in model_class._meta.concrete_fields if f.is_relation}
    if not fks or any(v is None for v in fks.values()):
        return "skipped"
    _, created = model_class.objects.get_or_create(**fks)
    return "created" if created else "skipped"
