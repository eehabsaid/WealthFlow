"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

instance_builder.py: turns one raw JSON row into kwargs suitable for
Model(**kwargs) or update_or_create(defaults=…), resolving ContentType
labels and __username hints along the way.
"""

from __future__ import annotations

from django.contrib.auth.models import User as UserModel

from core.services.backup_serializer import resolve_content_type
from core.services.restore.helpers import coerce_field


def build_instance_kwargs(
    row: dict,
    field_map: dict,
    model_class,
    username_cache: dict[str, UserModel],
) -> dict:
    """
    Convert one raw JSON row into kwargs suitable for Model(**kwargs) or
    update_or_create(defaults=…).

    Handles:
    - Type coercion for dates, datetimes, decimals, binary.
    - ContentType label resolution.
    - User FK resolution via __username hints.
    - auto_now_add / auto_now field overrides (stored as regular values).
    """
    from django.db import models as dm

    kwargs: dict = {}

    for attname, field in field_map.items():
        # Skip auto-generated PKs — they will be set explicitly from row["id"]
        # only when pk is in the row.  auto_now_add / auto_now fields cannot
        # be set on save but we pre-fill them via update_fields on the object.
        raw = row.get(attname)
        kwargs[attname] = coerce_field(field, raw)

    # --- Resolve content_type_id from label (Document model) ---------------
    if "_content_type_label" in row and "content_type_id" in kwargs:
        ct = resolve_content_type(row["_content_type_label"])
        kwargs["content_type_id"] = ct.pk if ct else None

    # --- Resolve User FKs from __username hints ----------------------------
    for attname, field in field_map.items():
        if (
            isinstance(field, (dm.ForeignKey, dm.OneToOneField))
            and field.related_model is UserModel
            and attname.endswith("_id")
        ):
            base_name = attname[:-3]  # e.g. "user_id" → "user"
            username_key = f"__{base_name}__username"
            if username_key in row and row[username_key]:
                username = row[username_key]
                if username not in username_cache:
                    try:
                        username_cache[username] = UserModel.objects.get(username=username)
                    except UserModel.DoesNotExist:
                        username_cache[username] = None
                user_obj = username_cache[username]
                kwargs[attname] = user_obj.pk if user_obj else None

    _resolve_natural_hints(row, field_map, kwargs)
    return kwargs


def _resolve_natural_hints(row: dict, field_map: dict, kwargs: dict) -> None:
    """Map __<fk>__perm / __<fk>__group hints to the ids of THIS database (None when it no longer exists)."""
    from django.contrib.auth.models import Group, Permission

    for attname in field_map:
        base = attname[:-3] if attname.endswith("_id") else attname
        perm_hint, group_hint = row.get(f"__{base}__perm"), row.get(f"__{base}__group")
        if perm_hint:
            try:
                app_label, model, codename = perm_hint.split(".", 2)
                kwargs[attname] = Permission.objects.get(content_type__app_label=app_label, content_type__model=model, codename=codename).pk
            except (ValueError, Permission.DoesNotExist):
                kwargs[attname] = None
        elif group_hint:
            kwargs[attname] = Group.objects.filter(name=group_hint).values_list("pk", flat=True).first()
