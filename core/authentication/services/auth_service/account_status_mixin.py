"""Account enable/disable workflow phases."""

from django.utils import timezone


class AccountStatusMixin:
    """Account disable/enable transitions."""

    @classmethod
    def disable_user(cls, user, actor=None, reason: str = "") -> None:
        profile = cls.get_profile(user)
        profile.account_status = "disabled"
        profile.disabled_at = timezone.now()
        profile.disabled_by = actor
        profile.status_reason = reason
        profile.save()
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
        cls.record_audit(user, "account_disabled", actor=actor, details=reason)

    @classmethod
    def enable_user(cls, user, actor=None, reason: str = "") -> None:
        profile = cls.get_profile(user)
        if profile.email_verified:
            profile.account_status = "active"
            user.is_active = True
        else:
            profile.account_status = "pending_email_verification"
            user.is_active = False
        profile.disabled_at = None
        profile.disabled_by = None
        profile.status_reason = reason
        profile.save()
        user.save(update_fields=["is_active"])
        cls.record_audit(user, "account_reenabled", actor=actor, details=reason)
