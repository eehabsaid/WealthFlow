"""One-time copy of settings a host kept in its own key/value table into AISetting.

Set AI_LEGACY_SETTINGS_MODEL = "app_label.Model" (fields key, value, description, owner). Rows whose key
starts with one of AI_SETTING_PREFIXES are copied once; old rows are never changed or deleted. A marker row
makes the copy run once; rows already in AISetting win over the copied ones.
"""
from django.apps import apps
from django.conf import settings

MARKER_KEY = "ai_legacy_settings_copied"
DEFAULT_PREFIXES = ("ai_", "speech_", "image_gen_")


def copy_legacy_settings(using="default") -> int:
    path = getattr(settings, "AI_LEGACY_SETTINGS_MODEL", None)
    if not path:
        return 0
    from django.db import connections

    from ai.models import AISetting
    if AISetting._meta.db_table not in connections[using].introspection.table_names():
        return 0   # e.g. after `migrate ai 0001` (reverse): the table is gone, nothing to copy into
    if AISetting.objects.using(using).filter(key=MARKER_KEY, owner=None).exists():
        return 0
    try:
        legacy = apps.get_model(path)
        rows = list(legacy.objects.using(using).all().values("key", "value", "description", "owner_id"))
    except Exception:  # model/table not there (yet): nothing to copy, try again on the next migrate
        return 0
    prefixes = tuple(getattr(settings, "AI_SETTING_PREFIXES", DEFAULT_PREFIXES))
    copied = 0
    for row in rows:
        if not row["key"].startswith(prefixes):
            continue
        _, created = AISetting.objects.using(using).get_or_create(
            key=row["key"], owner_id=row["owner_id"],
            defaults={"value": row["value"], "description": row["description"]})
        copied += int(created)
    AISetting.objects.using(using).get_or_create(key=MARKER_KEY, owner=None, defaults={"value": "1"})
    return copied


def post_migrate_copy(sender, using="default", **kwargs):
    if getattr(sender, "label", "") == "ai":
        copy_legacy_settings(using)
