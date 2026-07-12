"""
backup_data.py  –  Django management command
=============================================
Usage
-----
    python manage.py backup_data
    python manage.py backup_data --output ./my_backups/
    python manage.py backup_data --filename my_custom_name.wfbackup
    python manage.py backup_data --exclude authtoken,authauditlog
    python manage.py backup_data --no-compress

What it produces
----------------
A single self-contained `.wfbackup` file (ZIP archive) with:
  • One JSON file per model table  (numbered for import order)
  • manifest.json                  (metadata, row counts, SHA-256 checksums)
  • schema_version.txt             (last applied migration)

Special data handling
---------------------
  • Arabic / Unicode text  → ensure_ascii=False; no data mutation
  • DateField              → ISO 8601 "YYYY-MM-DD"
  • DateTimeField          → ISO 8601 with timezone offset
  • DecimalField           → String ("12345.67") – lossless
  • BinaryField            → Base64-encoded ASCII string
  • content_type FK        → "app_label.model_name" label string
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import zipfile
from datetime import datetime, timezone
from typing import Any

import django
from django.core.management.base import BaseCommand, CommandError
from django.db import models as django_models
from django.contrib.contenttypes.models import ContentType

from core.services.backup_serializer import (
    get_model_export_order,
    serialize_value,
    content_type_label,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_field_map(model_class) -> dict[str, django_models.Field]:
    """Return {field.attname: field} for all concrete fields on a model."""
    return {f.attname: f for f in model_class._meta.get_fields()
            if isinstance(f, django_models.Field) and not f.many_to_many and getattr(f, "concrete", True)}


def _serialize_instance(instance, field_map: dict) -> dict[str, Any]:
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


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_last_migration() -> str:
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


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Create a portable .wfbackup archive of all WealthFlow application "
        "data. The backup is database-agnostic and can be restored on any "
        "supported database engine."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="./backups/",
            help="Directory in which to write the .wfbackup file "
                 "(default: ./backups/).",
        )
        parser.add_argument(
            "--filename",
            default="",
            help="Override the auto-generated filename "
                 "(e.g. mybackup.wfbackup).",
        )
        parser.add_argument(
            "--exclude",
            default="",
            help="Comma-separated model names to skip "
                 "(e.g. authtoken,authauditlog,goldprice).",
        )
        parser.add_argument(
            "--no-compress",
            action="store_true",
            default=False,
            help="Store files uncompressed inside the ZIP (faster but larger).",
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        output_dir: str = options["output"]
        custom_filename: str = options["filename"].strip()
        exclude_raw: str = options["exclude"]
        no_compress: bool = options["no_compress"]

        excluded = {n.strip().lower() for n in exclude_raw.split(",") if n.strip()}

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Decide output path
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = custom_filename or f"wealthflow_backup_{ts}.wfbackup"
        output_path = os.path.join(output_dir, filename)

        compression = (
            zipfile.ZIP_STORED if no_compress else zipfile.ZIP_DEFLATED
        )

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*60}\n"
            f"  WealthFlow Backup\n"
            f"  Output : {output_path}\n"
            f"{'='*60}"
        ))

        export_order = get_model_export_order()

        manifest_rows: dict[str, int] = {}
        checksum_map: dict[str, str] = {}

        with zipfile.ZipFile(output_path, "w", compression=compression,
                             allowZip64=True) as zf:

            for prefix, model_class, _ in export_order:
                model_name = model_class.__name__.lower()
                if model_name in excluded:
                    self.stdout.write(f"  SKIP  {model_class.__name__}")
                    continue

                field_map = _get_field_map(model_class)
                queryset = model_class.objects.all()
                rows = [_serialize_instance(obj, field_map) for obj in queryset]

                entry_name = f"{prefix}_{model_name}.json"
                json_bytes = json.dumps(
                    {
                        "model": f"{model_class._meta.app_label}.{model_class.__name__}",
                        "count": len(rows),
                        "rows": rows,
                    },
                    ensure_ascii=False,   # ← Arabic text is preserved as-is
                    indent=2,
                ).encode("utf-8")

                zf.writestr(entry_name, json_bytes)
                checksum_map[entry_name] = _sha256_of_bytes(json_bytes)
                manifest_rows[model_class.__name__] = len(rows)

                label = model_class.__name__.ljust(35)
                self.stdout.write(f"  OK    {label} {len(rows):>7,} rows")

            # ── schema_version.txt ──────────────────────────────────────
            last_migration = _get_last_migration()
            zf.writestr("schema_version.txt", last_migration.encode("utf-8"))

            # ── manifest.json ───────────────────────────────────────────
            manifest = {
                "wealthflow_backup_version": "1.0",
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "django_version": django.get_version(),
                "last_migration": last_migration,
                "excluded_models": sorted(excluded),
                "row_counts": manifest_rows,
                "checksums": checksum_map,
            }
            manifest_bytes = json.dumps(
                manifest, ensure_ascii=False, indent=2
            ).encode("utf-8")
            zf.writestr("manifest.json", manifest_bytes)

        # ── Summary ────────────────────────────────────────────────────────
        total_rows = sum(manifest_rows.values())
        file_size_kb = os.path.getsize(output_path) / 1024
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  Backup complete!\n"
            f"  File    : {output_path}\n"
            f"  Size    : {file_size_kb:,.1f} KB\n"
            f"  Tables  : {len(manifest_rows)}\n"
            f"  Rows    : {total_rows:,}\n"
            f"{'='*60}\n"
        ))
