"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

table_restore.py: restores all rows for a single model — bulk_create
(ignore_conflicts), natural-key update, or update_or_create-by-PK depending
on the --overwrite flag.
"""

from __future__ import annotations

from core.services.restore.helpers import get_field_map
from core.services.restore.instance_builder import build_instance_kwargs


def restore_table(
    model_class,
    lookup_field: str | None,
    rows: list[dict],
    overwrite: bool,
    dry_run: bool,
    username_cache: dict,
) -> tuple[int, int, int]:
    """
    Restore rows for a single model.
    Returns (created, updated, skipped) counts.
    """
    field_map = get_field_map(model_class)
    created = updated = skipped = 0

    for row in rows:
        kwargs = build_instance_kwargs(row, field_map, model_class, username_cache)

        if dry_run:
            created += 1
            continue

        if overwrite and lookup_field:
            # Match using natural key to avoid modifying PKs on existing rows (which triggers INSERTs in Django)
            lookup_value = kwargs.get(lookup_field)
            if lookup_value is None:
                lookup_value = row.get(lookup_field)

            try:
                existing_instance = model_class.objects.get(**{lookup_field: lookup_value})
                # Update existing instance fields (except the PK id and the lookup field itself)
                for k, v in kwargs.items():
                    if k != "id" and k != lookup_field:
                        setattr(existing_instance, k, v)
                existing_instance.save()
                updated += 1
            except model_class.DoesNotExist:
                # Create as new instance with backup's PK.
                # If another record already holds this PK, delete it to prevent unique ID collision.
                pk_name = model_class._meta.pk.name
                pk_val = kwargs.get(pk_name) or row.get(pk_name) or kwargs.get("id") or row.get("id")
                if pk_val is not None:
                    model_class.objects.filter(**{pk_name: pk_val}).delete()

                model_class.objects.create(**kwargs)
                created += 1

        elif overwrite and not lookup_field:
            # update_or_create by PK
            pk_val = kwargs.get("id") or row.get("id")
            if pk_val is None:
                # No PK: just create
                try:
                    model_class.objects.create(**kwargs)
                    created += 1
                except Exception:
                    skipped += 1
            else:
                defaults = {k: v for k, v in kwargs.items() if k != "id"}
                _, was_created = model_class.objects.update_or_create(
                    id=pk_val,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        else:
            # Default: bulk_create with ignore_conflicts (skip existing PKs)
            try:
                obj = model_class(**kwargs)
                model_class.objects.bulk_create([obj], ignore_conflicts=True)
                created += 1
            except Exception:
                skipped += 1

    return created, updated, skipped
