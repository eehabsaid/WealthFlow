"""'Delete my account': irreversible removal of the user and everything they own."""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.db import transaction

from core.services.account.scope import AXES_MODELS, owned_queryset

logger = logging.getLogger(__name__)

LAST_ADMIN_MESSAGE = "You are the only administrator. Make another user an administrator before deleting this account."


def _is_admin(user) -> bool:
    profile = getattr(user, "profile", None)
    return bool(user.is_superuser or getattr(profile, "is_sysadmin", False))


def deletion_blocker(user) -> str | None:
    """Reason this account may not be self-deleted, or None. Never leave the platform without an active admin."""
    if not _is_admin(user):
        return None
    others = User.objects.filter(is_active=True).exclude(pk=user.pk)
    if any(_is_admin(u) for u in others.select_related("profile")):
        return None
    return LAST_ADMIN_MESSAGE


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
