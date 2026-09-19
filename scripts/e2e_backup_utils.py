"""
Django setup and pre-test database backup/restore helpers for the human
QA E2E suite entrypoint.

Split out of the former monolithic scripts/test_ui_human_full_e2e.py
(200-line rule). Kept as a flat sibling file, imported with a bare
`import` (no `scripts.` prefix) since test_ui_human_full_e2e.py is
invoked directly (`python scripts/test_ui_human_full_e2e.py`), which
puts the scripts/ directory itself on sys.path rather than the repo
root.
"""

import os


def setup_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wealthflow.settings')
    import django
    django.setup()


def create_pre_test_backup():
    from django.core.management import call_command
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    filename = "e2e_pre_test_auto_backup.wfbackup"
    filepath = os.path.join(backup_dir, filename)
    print(f"\n[BACKUP] Creating pre-test database backup: {filepath}")
    call_command("backup_data", output=backup_dir, filename=filename)
    return filepath


def restore_pre_test_backup(filepath):
    if filepath and os.path.exists(filepath):
        from django.core.management import call_command
        print(f"\n[RESTORE] Restoring database backup to clean state: {filepath}")
        call_command("restore_data", filepath, overwrite=True)
        print("[RESTORE OK] Database successfully restored to pre-test state!")
