"""
Umbrella re-export for the restore-data support package used by the
`restore_data` management command (core/management/commands/restore_data.py).

NOTE: 200-line-per-file convention — this package exists because the
original core/management/commands/restore_data.py (476 lines) exceeded the
project's 200-line ceiling. Django requires the management command itself
to remain a single flat file at commands/restore_data.py (that's how
Django's command loader discovers it), so all the row-level restore logic
and orchestration phases were moved here instead, leaving the command file
as a thin Command class that calls into this package.

Sibling files:
  - context.py            RestoreRunContext (per-run options + stdout/style)
                           and RestoreTotals (created/updated/skipped/tables)
                           dataclass carriers, mirroring the project's
                           mixin/phase dataclass-carrier convention.
  - helpers.py             sha256_of_bytes, get_field_map, coerce_field —
                           low-level type coercion for one field/value.
  - instance_builder.py    build_instance_kwargs — turns one raw JSON row
                           into Model(**kwargs), resolving ContentType and
                           __username hints.
  - table_restore.py       restore_table — per-row restore loop for a
                           single model (bulk_create / update_or_create /
                           natural-key update depending on --overwrite).
  - manifest_phase.py      validate_manifest — opens the manifest, checks
                           the migration marker, validates checksums, and
                           returns the sorted list of table files.
  - restore_loop_phase.py  run_restore_loop — disconnects signals, iterates
                           table files calling restore_table, reconnects
                           signals, returns RestoreTotals.

Only the names actually imported by restore_data.py are re-exported below.
"""

from core.services.restore.context import RestoreRunContext, RestoreTotals
from core.services.restore.manifest_phase import validate_manifest
from core.services.restore.restore_loop_phase import run_restore_loop

__all__ = [
    "RestoreRunContext",
    "RestoreTotals",
    "validate_manifest",
    "run_restore_loop",
]
