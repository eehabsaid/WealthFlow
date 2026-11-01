# Backups and restore
- `core/services/backup_serializer/export_order.py` lists every model in dependency order as `(prefix, Model, natural_key_field)`. Backup export and restore both walk it.
- A new model is NOT backed up until it is added there. `core/tests/system/test_backup_coverage.py` fails when a model is missing; add a round-trip test for the new model.
- Backups are `*.wfbackup` (git-ignored, folder `backups/`). Old backups must still restore: missing tables are skipped with a warning.
- Management commands: `manage.py backup_data`, `restore_data`.
- Tests: `core/tests/system/`.
