"""'Delete my account': soft-delete with a restorable grace period, then irreversible removal of the user and everything they own."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.constants.account_retention import grace_days, purge_at

from core.services.account.scope import AXES_MODELS, owned_queryset

logger = logging.getLogger(__name__)

PENDING_DELETION_STATUS = "pending_deletion"

LAST_ADMIN_MESSAGE = "You are the only administrator. Make another user an administrator before deleting this account."


def _is_admin(user) -> bool:
    profile = getattr(user, "profile", None)
    return bool(user.is_superuser or getattr(profile, "is_sysadmin", False))


def deletion_blocker(user) -> str | None:
    """Reason this account may not be self-deleted, or None. Never leave the platform without an active admin."""
    if not _is_admin(user):
        return None
    return None if _other_active_admin(user) else LAST_ADMIN_MESSAGE


def is_pending_deletion(user) -> bool:
    """Read from the DB so a profile object cached on `user` can never report a stale state."""
    from core.models import UserProfile

    return UserProfile.objects.filter(user=user, deletion_requested_at__isnull=False).exists()


def schedule_deletion(user, actor=None):
    """Soft-delete: disable the account and start the grace period. Data stays until purge_due_users()
    (or an admin's explicit purge). Returns the purge date. Callers check deletion_blocker() first."""
    from core.authentication.services import AuthWorkflowService

    profile = AuthWorkflowService.get_profile(user)
    if not profile.deletion_requested_at:
        profile.deletion_requested_at = timezone.now()
        before = profile.account_status
        if not user.is_active and before in ("active", PENDING_DELETION_STATUS):
            before = "disabled"
        profile.status_before_deletion = before
    profile.account_status = PENDING_DELETION_STATUS
    profile.save(update_fields=["deletion_requested_at", "status_before_deletion", "account_status", "updated_at"])
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    AuthWorkflowService.record_audit(user, "account_deletion_scheduled", actor=actor, details=f"grace_days={grace_days()}")
    return purge_at(profile)


def restore_needs_admin(user) -> bool:
    """True when the account was NOT active before deletion (disabled, rejected, awaiting approval): only an
    administrator may restore it, so self-service restore can never bypass an earlier admin decision."""
    from core.models import UserProfile

    before = UserProfile.objects.filter(user=user).values_list("status_before_deletion", flat=True).first()
    return bool(before) and before != "active"


def restore_user(user, actor=None) -> bool:
    """Cancel a scheduled deletion. The account returns to the state it had before the request: re-enabled if it
    was active, otherwise left disabled in its earlier status. False when it was not pending."""
    from core.authentication.services import AuthWorkflowService

    if not is_pending_deletion(user):
        return False
    profile = AuthWorkflowService.get_profile(user)
    before = profile.status_before_deletion or "active"
    profile.deletion_requested_at = None
    profile.status_before_deletion = ""
    if before == "active":
        profile.save(update_fields=["deletion_requested_at", "status_before_deletion", "updated_at"])
        AuthWorkflowService.enable_user(user, actor=actor, reason="restored after deletion request")
    else:
        profile.account_status = before
        profile.save(update_fields=["deletion_requested_at", "status_before_deletion", "account_status", "updated_at"])
    AuthWorkflowService.record_audit(user, "account_deletion_cancelled", actor=actor)
    return True


def purge_due_users(now=None) -> dict:
    """Scheduled job: purge every account whose grace period has ended. An administrator is kept
    (and logged) when purging would leave the platform without an active admin, so it can be restored."""
    now = now or timezone.now()
    cutoff = now - timedelta(days=grace_days())
    purged, kept = [], []
    due = User.objects.filter(profile__deletion_requested_at__isnull=False, profile__deletion_requested_at__lte=cutoff)
    for user in list(due.select_related("profile")):
        if _is_admin(user) and not _other_active_admin(user):
            logger.error("Purge skipped for %s: they are the last administrator", user.username)
            kept.append(user.username)
            continue
        purge_user(user)
        purged.append(user.username)
    return {"purged": len(purged), "kept_last_admin": kept}


def _other_active_admin(user) -> bool:
    others = User.objects.filter(is_active=True).exclude(pk=user.pk)
    return any(_is_admin(u) for u in others.select_related("profile"))


def purge_user(user) -> dict:
    """Delete rows FK-cascade would miss (SET_NULL / generic / username-keyed), then the user (cascades the rest).
    Shared by self-service deletion and the admin Users screen, so no path leaves orphaned financial data."""
    from core.models import AIPrompt, CurrencyExchange, Document

    username, counts = user.username, {}
    with transaction.atomic():
        for model in (Document, CurrencyExchange, AIPrompt, *_axes_models()):
            counts[model.__name__] = owned_queryset(model, user).delete()[0]
        user.delete()
    logger.warning("Account deleted: %s (%s)", username, counts)
    return counts


def _axes_models():
    from django.apps import apps

    return [m for m in apps.get_models() if m.__name__ in AXES_MODELS]
