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
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.services.backup_serializer import (
    get_model_export_order,
    deserialize_date,
    deserialize_datetime,
    deserialize_decimal,
    deserialize_binary,
    resolve_content_type,
    disconnect_restore_signals,
    reconnect_signals,
    run_post_restore_sync,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_field_map(model_class) -> dict:
    """Return {attname: field} for all concrete fields."""
    from django.db import models as dm
    return {f.attname: f for f in model_class._meta.get_fields()
            if isinstance(f, dm.Field) and not f.many_to_many and getattr(f, "concrete", True)}


def _coerce_field(field, raw_value: Any) -> Any:
    """Convert a raw JSON value to the correct Python type for a given field."""
    from django.db import models as dm

    if raw_value is None:
        return None

    if isinstance(field, (dm.DateTimeField,)):
        return deserialize_datetime(raw_value) if isinstance(raw_value, str) else raw_value

    if isinstance(field, (dm.DateField,)):
        return deserialize_date(raw_value) if isinstance(raw_value, str) else raw_value

    if isinstance(field, (dm.DecimalField,)):
        return deserialize_decimal(raw_value)

    if isinstance(field, (dm.BinaryField,)):
        return deserialize_binary(raw_value) if isinstance(raw_value, str) else raw_value

    return raw_value


def _build_instance_kwargs(
    row: dict,
    field_map: dict,
    model_class,
    username_cache: dict[str, User],
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
    from django.contrib.auth.models import User as UserModel

    kwargs: dict = {}

    for attname, field in field_map.items():
        # Skip auto-generated PKs — they will be set explicitly from row["id"]
        # only when pk is in the row.  auto_now_add / auto_now fields cannot
        # be set on save but we pre-fill them via update_fields on the object.
        raw = row.get(attname)
        kwargs[attname] = _coerce_field(field, raw)

    # --- Resolve content_type_id from label (Document model) ---------------
    if "_content_type_label" in row and "content_type_id" in kwargs:
        ct = resolve_content_type(row["_content_type_label"])
        kwargs["content_type_id"] = ct.pk if ct else None

    # --- Resolve User FKs from __username hints ----------------------------
    for attname, field in field_map.items():
        if (isinstance(field, (dm.ForeignKey, dm.OneToOneField))
                and field.related_model is UserModel
                and attname.endswith("_id")):
            base_name = attname[:-3]  # e.g. "user_id" → "user"
            username_key = f"__{base_name}__username"
            if username_key in row and row[username_key]:
                username = row[username_key]
                if username not in username_cache:
                    try:
                        username_cache[username] = UserModel.objects.get(
                            username=username
                        )
                    except UserModel.DoesNotExist:
                        username_cache[username] = None
                user_obj = username_cache[username]
                kwargs[attname] = user_obj.pk if user_obj else None

    return kwargs


# ---------------------------------------------------------------------------
# Core restore logic for a single table file
# ---------------------------------------------------------------------------

def _restore_table(
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
    field_map = _get_field_map(model_class)
    created = updated = skipped = 0

    for row in rows:
        kwargs = _build_instance_kwargs(row, field_map, model_class, username_cache)

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
                model_class.objects.bulk_create(
                    [obj], ignore_conflicts=True
                )
                created += 1
            except Exception:
                skipped += 1

    return created, updated, skipped


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

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

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        backup_file: str = options["backup_file"]
        dry_run: bool = options["dry_run"]
        tables_filter_raw: str = options["tables"]
        skip_users: bool = options["skip_users"]
        overwrite: bool = options["overwrite"]

        if not os.path.isfile(backup_file):
            raise CommandError(f"Backup file not found: {backup_file}")

        if not zipfile.is_zipfile(backup_file):
            raise CommandError(
                f"File does not appear to be a valid .wfbackup archive: "
                f"{backup_file}"
            )

        tables_filter = {
            t.strip().lower() for t in tables_filter_raw.split(",") if t.strip()
        }

        mode_label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*60}\n"
            f"  {mode_label}WealthFlow Restore\n"
            f"  Source : {backup_file}\n"
            f"{'='*60}"
        ))

        with zipfile.ZipFile(backup_file, "r") as zf:
            names = zf.namelist()

            # ── Read and validate manifest ──────────────────────────────
            if "manifest.json" not in names:
                raise CommandError("Invalid backup: manifest.json not found.")

            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            backup_version = manifest.get("wealthflow_backup_version", "?")
            self.stdout.write(
                f"  Backup version : {backup_version}\n"
                f"  Created at     : {manifest.get('created_at', '?')}\n"
                f"  Last migration : {manifest.get('last_migration', '?')}"
            )

            # Warn if migrations differ
            try:
                from django.db.migrations.recorder import MigrationRecorder
                last_local = (
                    MigrationRecorder.Migration.objects
                    .order_by("-applied")
                    .values_list("app", "name")
                    .first()
                )
                local_migration = (
                    f"{last_local[0]}.{last_local[1]}" if last_local else "none"
                )
            except Exception:
                local_migration = "unknown"

            if local_migration != manifest.get("last_migration"):
                self.stdout.write(self.style.WARNING(
                    f"\n  [!] Migration mismatch!\n"
                    f"     Backup : {manifest.get('last_migration')}\n"
                    f"     Local  : {local_migration}\n"
                    f"     Proceeding -- but review your schema carefully.\n"
                ))

            # -- Checksum validation -------------------------------------
            checksums = manifest.get("checksums", {})
            self.stdout.write("\n  Validating checksums ...")
            checksum_ok = True
            for entry_name, expected_hash in checksums.items():
                if entry_name not in names:
                    self.stdout.write(self.style.WARNING(
                        f"  [!] {entry_name} listed in manifest but missing from archive"
                    ))
                    continue
                actual_hash = _sha256_of_bytes(zf.read(entry_name))
                if actual_hash != expected_hash:
                    self.stdout.write(self.style.ERROR(
                        f"  FAIL  Checksum FAILED for {entry_name}"
                    ))
                    checksum_ok = False
            if not checksum_ok:
                raise CommandError(
                    "Backup archive is corrupted (checksum mismatch). "
                    "Restore aborted."
                )
            self.stdout.write(self.style.SUCCESS("  OK  All checksums valid"))

            # -- Sort table files in numeric prefix order -----------------
            table_files = sorted(
                [n for n in names if re.match(r"^\d{2}_.*\.json$", n)]
            )

            # ── Build model lookup from export order ─────────────────────
            export_order = get_model_export_order()
            prefix_to_meta = {}
            for prefix, model_class, lookup_field in export_order:
                key = model_class.__name__.lower()
                prefix_to_meta[key] = (model_class, lookup_field)

            # ── Disconnect signals before restore ────────────────────────
            disconnected_signals = []
            if not dry_run:
                disconnected_signals = disconnect_restore_signals()

            # ── Restore loop ─────────────────────────────────────────────
            username_cache: dict[str, User] = {}
            total_created = total_updated = total_skipped = 0
            tables_restored = 0

            self.stdout.write(f"\n  {'='*56}")

            try:
                for entry_name in table_files:
                    # Extract model name from filename: "01_user.json" → "user"
                    model_name = re.sub(r"^\d{2}_(.+)\.json$", r"\1", entry_name)

                    # Apply --tables filter
                    if tables_filter and model_name not in tables_filter:
                        continue

                    # Apply --skip-users
                    if skip_users and model_name in ("user", "group"):
                        self.stdout.write(f"  SKIP  {model_name} (--skip-users)")
                        continue

                    if model_name not in prefix_to_meta:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [!] Unknown model in archive: {model_name} -- skipping"
                            )
                        )
                        continue

                    model_class, lookup_field = prefix_to_meta[model_name]

                    # Read and parse the JSON payload
                    raw_bytes = zf.read(entry_name)
                    payload = json.loads(raw_bytes.decode("utf-8"))
                    rows = payload.get("rows", [])

                    with transaction.atomic():
                        created, updated, skipped = _restore_table(
                            model_class=model_class,
                            lookup_field=lookup_field,
                            rows=rows,
                            overwrite=overwrite,
                            dry_run=dry_run,
                            username_cache=username_cache,
                        )

                    total_created += created
                    total_updated += updated
                    total_skipped += skipped
                    tables_restored += 1

                    label = model_class.__name__.ljust(35)
                    detail = (
                        f"created={created:>5}  updated={updated:>5}  "
                        f"skipped={skipped:>5}"
                    )
                    self.stdout.write(f"  OK    {label}  {detail}")

            finally:
                # Always reconnect signals, even if an error occurred
                if not dry_run:
                    reconnect_signals(disconnected_signals)

            # -- Post-restore sync ----------------------------------------
            if not dry_run:
                self.stdout.write("\n  Running post-restore balance sync ...")
                try:
                    run_post_restore_sync()
                    self.stdout.write(self.style.SUCCESS(
                        "  OK  Balance sync complete"
                    ))
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f"  [!] Balance sync partial failure: {exc}"
                    ))

        # -- Final summary --------------------------------------------------
        dry_label = " (dry run -- nothing written)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  Restore complete{dry_label}\n"
            f"  Tables   : {tables_restored}\n"
            f"  Created  : {total_created:,}\n"
            f"  Updated  : {total_updated:,}\n"
            f"  Skipped  : {total_skipped:,}\n"
            f"{'='*60}\n"
        ))
