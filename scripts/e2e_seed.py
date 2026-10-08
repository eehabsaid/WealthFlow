"""Deterministic E2E fixtures, applied to the DISPOSABLE test database only.

Run by scripts/run_full_e2e.py right after `migrate`, so the suite never depends on whatever
state the developer's local db.sqlite3 happens to be in (and works when db.sqlite3 is untracked).

Rules: never touches db.sqlite3 (refuses to run against it), never calls set_password on an existing user,
only creates what is missing, and always resets the billing scenario state for `testuser`.
"""

import os
import sys
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wealthflow.settings")

ADMIN = ("eehab_said", "Eehabdev1")
TESTER = ("testuser", "Eehabdev1")


def _ensure_plans():
    from core.models import Plan

    if not Plan.objects.filter(is_active=True).exists():
        Plan.objects.get_or_create(code="basic", defaults={"name": "Basic", "sort_order": 1})
        Plan.objects.get_or_create(code="pro", defaults={"name": "Pro", "sort_order": 2, "allows_ai_workspace": True})


def _ensure_user(username, password, *, admin):
    from django.contrib.auth import get_user_model
    from core.models import UserProfile

    User = get_user_model()
    user = User.objects.filter(username=username).first()
    if user is None:
        user = User.objects.create_user(username=username, email=f"{username}@example.test", password=password)
        if admin:
            user.is_staff = user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
    if admin:
        UserProfile.objects.filter(user=user).update(is_sysadmin=True)
    return user


def _reset_billing_tester(user):
    from django.utils import timezone
    from core.models import PagePermission, Subscription
    from core.services.billing.subscription_service import SubscriptionService

    PagePermission.objects.filter(user=user).delete()
    Subscription.objects.filter(owner=user).delete()
    sub = SubscriptionService.start_trial(user)
    sub.trial_end = timezone.now() + timedelta(days=10)
    sub.save(update_fields=["trial_end", "updated_at"])


def main() -> int:
    import django

    django.setup()
    from django.conf import settings

    name = os.path.basename(str(settings.DATABASES["default"]["NAME"]))
    if name == "db.sqlite3":
        print("[e2e_seed] refusing to seed db.sqlite3 (set WEALTHFLOW_DB_NAME to the disposable DB)")
        return 2
    _ensure_plans()
    _ensure_user(*ADMIN, admin=True)
    _reset_billing_tester(_ensure_user(*TESTER, admin=False))
    print(f"[e2e_seed] seeded {name}: plans, {ADMIN[0]} (sysadmin), {TESTER[0]} (10-day trial, no page permissions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
