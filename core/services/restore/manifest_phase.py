"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

manifest_phase.py: reads manifest.json from the open archive, warns on a
migration-marker mismatch, validates every checksum, and returns the sorted
list of table files to restore.
"""

from __future__ import annotations

import json
import re

from django.core.management.base import CommandError

from core.services.restore.context import RestoreRunContext
from core.services.restore.helpers import sha256_of_bytes


def validate_manifest(zf, names: list[str], ctx: RestoreRunContext) -> dict:
    """
    Validate manifest.json and checksums for the open archive `zf`.
    Returns {"manifest": dict, "table_files": list[str]}.
    Raises CommandError if the archive is invalid or corrupted.
    """
    if "manifest.json" not in names:
        raise CommandError("Invalid backup: manifest.json not found.")

    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    backup_version = manifest.get("wealthflow_backup_version", "?")
    ctx.stdout.write(
        f"  Backup version : {backup_version}\n"
        f"  Created at     : {manifest.get('created_at', '?')}\n"
        f"  Last migration : {manifest.get('last_migration', '?')}"
    )

    # Warn if migrations differ
    try:
        from django.db.migrations.recorder import MigrationRecorder

        last_local = (
            MigrationRecorder.Migration.objects.order_by("-applied")
            .values_list("app", "name")
            .first()
        )
        local_migration = f"{last_local[0]}.{last_local[1]}" if last_local else "none"
    except Exception:
        local_migration = "unknown"

    if local_migration != manifest.get("last_migration"):
        ctx.stdout.write(
            ctx.style.WARNING(
                f"\n  [!] Migration mismatch!\n"
                f"     Backup : {manifest.get('last_migration')}\n"
                f"     Local  : {local_migration}\n"
                f"     Proceeding -- but review your schema carefully.\n"
            )
        )

    # -- Checksum validation -------------------------------------
    checksums = manifest.get("checksums", {})
    ctx.stdout.write("\n  Validating checksums ...")
    checksum_ok = True
    for entry_name, expected_hash in checksums.items():
        if entry_name not in names:
            ctx.stdout.write(
                ctx.style.WARNING(f"  [!] {entry_name} listed in manifest but missing from archive")
            )
            continue
        actual_hash = sha256_of_bytes(zf.read(entry_name))
        if actual_hash != expected_hash:
            ctx.stdout.write(ctx.style.ERROR(f"  FAIL  Checksum FAILED for {entry_name}"))
            checksum_ok = False
    if not checksum_ok:
        raise CommandError("Backup archive is corrupted (checksum mismatch). Restore aborted.")
    ctx.stdout.write(ctx.style.SUCCESS("  OK  All checksums valid"))

    # -- Sort table files in numeric prefix order -----------------
    table_files = sorted([n for n in names if re.match(r"^\d{2}_.*\.json$", n)])

    return {"manifest": manifest, "table_files": table_files}
