"""
restore_data.py  –  Django management command
=============================================
Usage
-----
    python manage.py restore_data path/to/backup.wfbackup
    python manage.py restore_data path/to/backup.wfbackup --dry-run
    python manage.py restore_data path/to/backup.wfbackup --tables currency,bank
    python manage.py restore_data path/to/backup.wfbackup --skip-users
    python manage.py restore_data path/to/backup.wfbackup --overwrite

What it does
------------
1. Opens the .wfbackup ZIP archive.
2. Validates the manifest (checksums, version check).
3. Processes table files in numeric prefix order.
4. For each table:
   • Deserialises JSON (UTF-8, Arabic text is preserved).
   • Decodes Base64 binary fields.
   • Parses ISO date/datetime strings.
   • Casts Decimal strings back to Decimal.
   • Resolves "app_label.model_name" → ContentType PK.
   • Resolves __username hints → User PKs.
   • bulk_create (ignore_conflicts) or update_or_create per --overwrite.
5. Reconnects signals and runs post-restore balance sync.

Options
-------
--dry-run    Validate and report without writing anything.
--tables     Comma-separated list of model names to restore (default: all).
--skip-users Skip auth.User and auth.Group records entirely.
--overwrite  Use update_or_create by PK (default: skip existing rows).

NOTE: this file must stay a single flat module directly under
management/commands/ — that's how Django's command loader discovers it by
name. To respect the project's 200-line ceiling, all row-level restore
logic and orchestration phases live in core/services/restore/ instead; this
file only parses options and calls into that package. See
core/services/restore/__init__.py for the full breakdown.
"""

from __future__ import annotations

import os
import zipfile

from django.core.management.base import BaseCommand, CommandError

from core.services.backup_serializer import run_post_restore_sync
from core.services.restore import RestoreRunContext, run_restore_loop, validate_manifest


class Command(BaseCommand):
    help = (
        "Restore WealthFlow application data from a .wfbackup archive. "
        "The restore is database-agnostic and handles Arabic text, ISO dates, "
        "Decimal precision, and Base64-encoded binary fields correctly."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            help="Path to the .wfbackup file to restore from.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Validate the backup and report what would be restored "
                 "without writing anything to the database.",
        )
        parser.add_argument(
            "--tables",
            default="",
            help="Comma-separated list of model names to restore "
                 "(default: all tables in the backup).",
        )
        parser.add_argument(
            "--skip-users",
            action="store_true",
            default=False,
            help="Skip auth.User and auth.Group records.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Overwrite existing records matched by PK or natural key. "
                 "Default is to skip existing records.",
        )

    def handle(self, *args, **options):
        backup_file: str = options["backup_file"]
        dry_run: bool = options["dry_run"]
        tables_filter_raw: str = options["tables"]
        skip_users: bool = options["skip_users"]
        overwrite: bool = options["overwrite"]

        if not os.path.isfile(backup_file):
            raise CommandError(f"Backup file not found: {backup_file}")

        if not zipfile.is_zipfile(backup_file):
            raise CommandError(f"File does not appear to be a valid .wfbackup archive: {backup_file}")

        tables_filter = {t.strip().lower() for t in tables_filter_raw.split(",") if t.strip()}
        ctx = RestoreRunContext(
            stdout=self.stdout,
            style=self.style,
            dry_run=dry_run,
            tables_filter=tables_filter,
            skip_users=skip_users,
            overwrite=overwrite,
        )

        mode_label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*60}\n"
            f"  {mode_label}WealthFlow Restore\n"
            f"  Source : {backup_file}\n"
            f"{'='*60}"
        ))

        with zipfile.ZipFile(backup_file, "r") as zf:
            names = zf.namelist()
            manifest_info = validate_manifest(zf, names, ctx)
            totals = run_restore_loop(zf, manifest_info["table_files"], ctx)

            if not dry_run:
                self.stdout.write("\n  Running post-restore balance sync ...")
                try:
                    run_post_restore_sync()
                    self.stdout.write(self.style.SUCCESS("  OK  Balance sync complete"))
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  [!] Balance sync partial failure: {exc}"))

        dry_label = " (dry run -- nothing written)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  Restore complete{dry_label}\n"
            f"  Tables   : {totals.tables_restored}\n"
            f"  Created  : {totals.created:,}\n"
            f"  Updated  : {totals.updated:,}\n"
            f"  Skipped  : {totals.skipped:,}\n"
            f"{'='*60}\n"
        ))
