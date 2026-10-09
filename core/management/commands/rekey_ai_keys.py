"""Re-encrypt stored AI/payment credentials from an old key to the current WEALTHFLOW_AI_ENCRYPTION_KEY.

Run once after setting a private key on the server (heavy logic lives in core/services/ai/credential_rekey.py):
    WEALTHFLOW_AI_ENCRYPTION_KEY=<new> python manage.py rekey_ai_keys            # dry run
    WEALTHFLOW_AI_ENCRYPTION_KEY=<new> python manage.py rekey_ai_keys --apply
Use --old-key <secret> when the previous key was itself a WEALTHFLOW_AI_ENCRYPTION_KEY value; omit it when the
credentials were stored under the default (SECRET_KEY-derived) key."""

from django.core.management.base import BaseCommand, CommandError

from core.services.ai.credential_encryption import using_default_key
from core.services.ai.credential_rekey import rekey_all


class Command(BaseCommand):
    help = "Re-encrypt stored AI provider keys and payment secrets under the current WEALTHFLOW_AI_ENCRYPTION_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--old-key", default=None, help="Previous WEALTHFLOW_AI_ENCRYPTION_KEY value (default: the SECRET_KEY-derived key).")
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")

    def handle(self, *args, **options):
        if using_default_key():
            raise CommandError("Set WEALTHFLOW_AI_ENCRYPTION_KEY to the NEW private key first, then run this command.")
        result = rekey_all(old_secret=options["old_key"], apply=options["apply"])
        if result["same_key"]:
            self.stdout.write("Old and current keys are the same: nothing to do.")
            return
        verb = "Re-encrypted" if result["applied"] else "Would re-encrypt (dry run, pass --apply)"
        self.stdout.write(f"{verb}: {result['rewritten']} | already on the current key: {result['already_current']}")
        if result["unreadable"]:
            self.stdout.write(self.style.WARNING("Could not read with either key (untouched, re-enter in Settings): " + ", ".join(result["unreadable"])))
