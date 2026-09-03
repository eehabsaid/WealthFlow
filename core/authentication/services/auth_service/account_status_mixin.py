"""Admin approval/rejection and account enable/disable workflow phases."""

from django.utils import timezone

from core.authentication.serializers import AuthFlowResult
from core.authentication.emails import EmailDeliveryError


class AccountStatusMixin:
    """Admin approve/reject and account disable/enable transitions."""

    @classmethod
    def approve_user(cls, raw_token: str, actor=None) -> AuthFlowResult:
        token, error_key = cls.resolve_token(raw_token, "admin_approve")
        if token is None:
            return AuthFlowResult(ok=False, error_key=error_key)

        user = token.user
        profile = cls.get_profile(user)
        profile.account_status = "active"
        profile.approved_at = timezone.now()
        profile.approved_by = actor
        profile.status_reason = ""
        profile.rejected_at = None
        profile.rejected_by = None
        profile.disabled_at = None
        profile.disabled_by = None
        profile.save()
        user.is_active = True
        user.save(update_fields=["is_active"])
        cls.mark_token_used(token)
        cls.record_audit(user, "admin_approved", actor=actor)
        context = cls._common_context(user, None, {"VerificationLink": "", "PasswordResetLink": ""})
        try:
            cls.send_template_email("account_approved", [user.email], profile.preferred_language or "en", context)
        except EmailDeliveryError:
            cls.record_audit(user, "admin_approved", actor=actor, details="approval_email_failed")
        return AuthFlowResult(ok=True, message_key="auth_account_approved_success", user=user, profile=profile)

    @classmethod
    def reject_user(cls, raw_token: str, actor=None) -> AuthFlowResult:
        token, error_key = cls.resolve_token(raw_token, "admin_reject")
        if token is None:
            return AuthFlowResult(ok=False, error_key=error_key)

        user = token.user
        profile = cls.get_profile(user)
        profile.account_status = "rejected"
        profile.rejected_at = timezone.now()
        profile.rejected_by = actor
        profile.status_reason = ""
        profile.save()
        user.is_active = False
        user.save(update_fields=["is_active"])
        cls.mark_token_used(token)
        cls.record_audit(user, "admin_rejected", actor=actor)
        context = cls._common_context(user, None, {"VerificationLink": "", "PasswordResetLink": ""})
        try:
            cls.send_template_email("account_rejected", [user.email], profile.preferred_language or "en", context)
        except EmailDeliveryError:
            cls.record_audit(user, "admin_rejected", actor=actor, details="rejection_email_failed")
        return AuthFlowResult(ok=True, message_key="auth_account_rejected_success", user=user, profile=profile)

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
