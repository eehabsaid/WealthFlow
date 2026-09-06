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

Note on file layout: field-mapping, instance-serialization, checksum, and
migration-lookup helpers live in core.services.backup_serializer (not in
this file) to keep this module under 200 lines. They can't be split into a
sibling package under management/commands/ instead, because Django's
management-command auto-discovery (pkgutil.iter_modules with
`not is_pkg`) only recognizes flat modules there, not packages.
"""

from __future__ import annotations

import json
import os
import platform
import zipfile
from datetime import datetime, timezone

import django
from django.core.management.base import BaseCommand

from core.services.backup_serializer import (
    get_model_export_order,
    get_field_map,
    serialize_instance,
    sha256_of_bytes,
    get_last_migration,
)


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
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
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

                field_map = get_field_map(model_class)
                queryset = model_class.objects.all()
                rows = [serialize_instance(obj, field_map) for obj in queryset]

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
                checksum_map[entry_name] = sha256_of_bytes(json_bytes)
                manifest_rows[model_class.__name__] = len(rows)

                label = model_class.__name__.ljust(35)
                self.stdout.write(f"  OK    {label} {len(rows):>7,} rows")

            # ── schema_version.txt ──────────────────────────────────────
            last_migration = get_last_migration()
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
