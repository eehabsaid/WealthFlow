"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

restore_loop_phase.py: disconnects signals, iterates the sorted table
files applying --tables / --skip-users filters, restores each table inside
its own transaction, reconnects signals, and returns the accumulated totals.
"""

from __future__ import annotations

import json
import re

from django.db import transaction

from core.services.backup_serializer import disconnect_restore_signals, get_model_export_order, reconnect_signals
from core.services.restore.context import RestoreRunContext, RestoreTotals
from core.services.restore.table_restore import restore_table


def run_restore_loop(zf, table_files: list[str], ctx: RestoreRunContext) -> RestoreTotals:
    """Restore every table file in `table_files` from the open archive `zf`."""
    export_order = get_model_export_order()
    prefix_to_meta = {}
    for _prefix, model_class, lookup_field in export_order:
        key = model_class.__name__.lower()
        prefix_to_meta[key] = (model_class, lookup_field)

    disconnected_signals = []
    if not ctx.dry_run:
        disconnected_signals = disconnect_restore_signals()

    username_cache: dict = {}
    totals = RestoreTotals(disconnected_signals=disconnected_signals)

    ctx.stdout.write(f"\n  {'='*56}")

    try:
        for entry_name in table_files:
            # Extract model name from filename: "01_user.json" → "user"
            model_name = re.sub(r"^\d{2}_(.+)\.json$", r"\1", entry_name)

            # Apply --tables filter
            if ctx.tables_filter and model_name not in ctx.tables_filter:
                continue

            # Apply --skip-users
            if ctx.skip_users and model_name in ("user", "group"):
                ctx.stdout.write(f"  SKIP  {model_name} (--skip-users)")
                continue

            if model_name not in prefix_to_meta:
                ctx.stdout.write(ctx.style.WARNING(f"  [!] Unknown model in archive: {model_name} -- skipping"))
                continue

            model_class, lookup_field = prefix_to_meta[model_name]

            # Read and parse the JSON payload
            raw_bytes = zf.read(entry_name)
            payload = json.loads(raw_bytes.decode("utf-8"))
            rows = payload.get("rows", [])

            with transaction.atomic():
                created, updated, skipped = restore_table(
                    model_class=model_class,
                    lookup_field=lookup_field,
                    rows=rows,
                    overwrite=ctx.overwrite,
                    dry_run=ctx.dry_run,
                    username_cache=username_cache,
                )

            totals.created += created
            totals.updated += updated
            totals.skipped += skipped
            totals.tables_restored += 1

            label = model_class.__name__.ljust(35)
            detail = f"created={created:>5}  updated={updated:>5}  skipped={skipped:>5}"
            ctx.stdout.write(f"  OK    {label}  {detail}")

    finally:
        # Always reconnect signals, even if an error occurred
        if not ctx.dry_run:
            reconnect_signals(disconnected_signals)

    return totals
