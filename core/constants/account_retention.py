"""Account-deletion grace period (light module: safe to import from request paths and from core.services.account)."""

from datetime import timedelta

GRACE_DAYS_KEY = "account_deletion_grace_days"
DEFAULT_GRACE_DAYS = 30


def grace_days() -> int:
    """Days a deleted account stays restorable (AppSettings `account_deletion_grace_days`, default 30)."""
    from core.models import AppSettings

    try:
        return max(0, int(str(AppSettings.get(GRACE_DAYS_KEY, DEFAULT_GRACE_DAYS)).strip()))
    except (TypeError, ValueError):
        return DEFAULT_GRACE_DAYS


def purge_at(profile):
    """When a pending-deletion account will be purged, or None."""
    if profile is None or not profile.deletion_requested_at:
        return None
    return profile.deletion_requested_at + timedelta(days=grace_days())
