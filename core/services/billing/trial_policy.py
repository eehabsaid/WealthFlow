"""Platform policy: do accounts created by a sysadmin get a trial?

Stored as a global AppSettings row (owner=NULL), editable in Settings > Billing. Default ON.
It only affects accounts created AFTER the setting is read: existing users are never touched (no backfill).
"""

from core.models import AppSettings

TRIAL_ON_ADMIN_CREATE_KEY = "trial_on_admin_created_users"


def admin_created_trial_enabled() -> bool:
    return str(AppSettings.get(TRIAL_ON_ADMIN_CREATE_KEY, "true")).strip().lower() not in ("false", "0", "no", "off")


def set_admin_created_trial_enabled(enabled: bool) -> None:
    AppSettings.set(TRIAL_ON_ADMIN_CREATE_KEY, "true" if enabled else "false")


def start_trial_for_admin_created(user):
    """Start a trial for a sysadmin-created account when the policy is on. Returns the Subscription or None.
    Platform operators (superusers / sysadmins) are never billed; a missing Plan catalog is not fatal."""
    from core.models import UserProfile
    from core.services.billing.subscription_service import SubscriptionService

    if not admin_created_trial_enabled() or user.is_superuser:
        return None
    profile = UserProfile.objects.filter(user=user).only("is_sysadmin").first()
    if profile and profile.is_sysadmin:
        return None
    try:
        return SubscriptionService.start_trial(user)
    except RuntimeError:
        return None
