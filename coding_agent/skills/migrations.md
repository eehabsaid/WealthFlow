# Migrations
- Numbered files in `core/migrations/` (`00NN_name.py`). Create with `python manage.py makemigrations core -n <name>`; check with `python manage.py makemigrations --check --dry-run` (must report no changes).
- Never edit or delete a migration that is already in the repo's history; add a new one. Protected by `coding_agent/config.json`.
- A new model must also be added to the backup order in `core/services/backup_serializer/export_order.py` or `core/tests/system/test_backup_coverage.py` fails.
- Data migrations must be reversible or say plainly why not. Never touch `db.sqlite3` by hand.
- After a model change, check `ai_knowledge/` (`python manage.py generate_ai_knowledge`) and revert incidental `ai_knowledge/` and `db.sqlite3` diffs before delivery.
