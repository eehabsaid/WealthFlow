"""Optional 'post due recurring transactions when I sign in' (per-user setting, default OFF).

Reuses RecurringService.preview_due / process_due unchanged; this module only decides whether to run them."""

import logging

from core.models import AppSettings
from core.services.budgets.recurring_service import RecurringService

logger = logging.getLogger(__name__)

AUTO_POST_KEY = "recurring_auto_post_on_login"


def is_auto_post_enabled(user) -> bool:
    return str(AppSettings.get(AUTO_POST_KEY, "false", user=user)).strip().lower() == "true"


def auto_post_on_login(user) -> int:
    """Post the user's due recurring transactions when they enabled it. Never raises: a failure here
    must not block sign-in. Returns the number of expenses created."""
    try:
        if not is_auto_post_enabled(user) or not RecurringService.preview_due(user):
            return 0
        created, _skipped = RecurringService.process_due(user)
        return len(created)
    except Exception:
        logger.exception("Recurring auto-post on login failed for user %s", getattr(user, "pk", None))
        return 0
