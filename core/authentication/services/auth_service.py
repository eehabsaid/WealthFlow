"""
Core authentication workflow service implementation.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.models import AppSettings, UserProfile
from core.authentication.serializers import AuthFlowResult
from core.authentication.tokens import (
    create_token,
    resolve_token,
    mark_token_used,
    hash_token,
)
from core.authentication.emails import (
    EmailDeliveryError,
    send_template_email,
    send_smtp_test_email,
    replace_placeholders,
)
from core.authentication.utils import record_audit

User = get_user_model()
logger = logging.getLogger(__name__)

PROFILE_STATUS_ERROR_KEYS = {
    "pending_email_verification": "auth_status_verify_email",
    "pending_admin_approval": "auth_status_pending_admin_approval",
    "rejected": "auth_status_rejected",
    "disabled": "auth_status_disabled",
}

class AuthWorkflowService:
    token_ttl = timedelta(hours=24)

    @staticmethod
    def get_profile(user) -> UserProfile:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.account_status:
            profile.account_status = "active" if user.is_active else "disabled"
            profile.save(update_fields=["account_status", "updated_at"])
        return profile

    @staticmethod
    def replace_placeholders(text: str, context: dict) -> str:
        return replace_placeholders(text, context)

    @classmethod
    def _hash_token(cls, raw_token: str) -> str:
        return hash_token(raw_token)

    @classmethod
    def create_token(cls, user, purpose: str) -> str:
        return create_token(user, purpose, cls.token_ttl)

    @classmethod
    def resolve_token(cls, raw_token: str, purpose: str):
        return resolve_token(raw_token, purpose)

    @classmethod
    def mark_token_used(cls, token) -> None:
        mark_token_used(token)

    @classmethod
    def record_audit(cls, user, event_type: str, actor=None, details: str = "") -> None:
        record_audit(user, event_type, actor=actor, details=details)

    @classmethod
    def send_template_email(cls, template_key: str, to_emails: list[str], lang: str, context: dict) -> str:
        return send_template_email(template_key, to_emails, lang, context)

    @classmethod
    def send_smtp_test_email(cls, *, to_email: str) -> tuple[bool, str]:
        return send_smtp_test_email(to_email=to_email)

    @classmethod
    def _admin_notification_email(cls) -> str:
        configured = AppSettings.get("administrator_notification_email", "")
        if configured:
            return configured
        admin_user = User.objects.filter(is_staff=True).exclude(email="").order_by("id").first()
        return admin_user.email if admin_user else ""

    @classmethod
    def _common_context(cls, user, request, extra: dict | None = None) -> dict:
        year = timezone.now().year
        profile = cls.get_profile(user)
        context = {
            "UserName": profile.display_name(),
            "Email": user.email,
            "AppName": "WealthFlow",
            "CurrentYear": year,
            "ApprovalDate": timezone.now().date().isoformat(),
            "RegistrationDate": user.date_joined.date().isoformat() if user.date_joined else "",
        }
        if extra:
            context.update(extra)
        return context

    @classmethod
    def register_user(cls, request, *, username: str, email: str, password: str, confirm_password: str, full_name: str = "", lang: str = "en") -> AuthFlowResult:
        username = username.strip()
        email = email.strip().lower()
        full_name = full_name.strip()

        if not username or not email or not password:
            return AuthFlowResult(ok=False, error_key="auth_error_required_signup_fields")
        if password != confirm_password:
            return AuthFlowResult(ok=False, error_key="auth_error_passwords_mismatch")
        if User.objects.filter(username=username).exists():
            return AuthFlowResult(ok=False, error_key="auth_error_username_taken")

        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            existing_profile = cls.get_profile(existing_user)
            error_key = PROFILE_STATUS_ERROR_KEYS.get(existing_profile.account_status, "auth_error_email_registered")
            return AuthFlowResult(
                ok=False,
                error_key=error_key,
                user=existing_user,
                profile=existing_profile,
                extra={
                    "show_forgot_password": True,
                    "prefill_email": email,
                },
            )

        try:
            validate_password(password)
        except ValidationError:
            return AuthFlowResult(ok=False, error_key="auth_error_password_validation")

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
            profile = cls.get_profile(user)
            profile.full_name = full_name
            profile.email_verified = False
            profile.account_status = "pending_email_verification"
            profile.preferred_language = lang
            profile.status_reason = ""
            profile.approved_at = None
            profile.rejected_at = None
            profile.disabled_at = None
            profile.save()
            cls.record_audit(user, "registration", details="pending_email_verification")

        verify_token = cls.create_token(user, "email_verification")
        verify_link = request.build_absolute_uri(reverse("verify_email", args=[verify_token]))
        context = cls._common_context(user, request, {"VerificationLink": verify_link, "PasswordResetLink": ""})
        try:
            cls.send_template_email("email_verification", [user.email], lang, context)
        except EmailDeliveryError:
            user.delete()
            return AuthFlowResult(ok=False, error_key="auth_email_delivery_failed")

        try:
            cls.send_template_email("welcome_email", [user.email], lang, context)
        except EmailDeliveryError:
            cls.record_audit(user, "registration", details="welcome_email_failed")

        return AuthFlowResult(ok=True, message_key="auth_signup_success_verify_email", user=user, profile=profile)

    @classmethod
    def get_login_block(cls, user) -> str:
        if user is None:
            return "auth_error_invalid_login"
        profile = cls.get_profile(user)
        if not profile.email_verified:
            return "auth_status_verify_email"
        if profile.account_status == "pending_admin_approval":
            return "auth_status_pending_admin_approval"
        if profile.account_status == "rejected":
            return "auth_status_rejected"
        if profile.account_status == "disabled" or not user.is_active:
            return "auth_status_disabled"
        return "auth_error_invalid_login"

    @classmethod
    def verify_email(cls, request, raw_token: str) -> AuthFlowResult:
        token, error_key = cls.resolve_token(raw_token, "email_verification")
        if token is None:
            return AuthFlowResult(ok=False, error_key=error_key)

        user = token.user
        profile = cls.get_profile(user)
        profile.email_verified = True
        if profile.account_status == "pending_email_verification":
            profile.account_status = "pending_admin_approval"
        profile.preferred_language = profile.preferred_language or AppSettings.get("active_language", "en") or "en"
        profile.save(update_fields=["email_verified", "account_status", "preferred_language", "updated_at"])
        cls.mark_token_used(token)
        cls.record_audit(user, "email_verified", details="pending_admin_approval")

        approve_token = cls.create_token(user, "admin_approve")
        reject_token = cls.create_token(user, "admin_reject")
        approve_link = request.build_absolute_uri(reverse("admin_approve_account", args=[approve_token]))
        reject_link = request.build_absolute_uri(reverse("admin_reject_account", args=[reject_token]))

        admin_email = cls._admin_notification_email()
        if admin_email:
            context = cls._common_context(
                user,
                request,
                {
                    "VerificationLink": approve_link,
                    "PasswordResetLink": reject_link,
                    "ApproveLink": approve_link,
                    "RejectLink": reject_link,
                    "EmailVerified": "Yes",
                },
            )
            try:
                cls.send_template_email("admin_approval_request", [admin_email], profile.preferred_language or "en", context)
            except EmailDeliveryError:
                cls.record_audit(user, "email_verified", details="pending_admin_approval_admin_notification_failed")

        return AuthFlowResult(ok=True, message_key="auth_verify_success_pending_admin", user=user, profile=profile)

    @classmethod
    def request_password_reset(cls, request, identifier: str, lang: str = "en") -> AuthFlowResult:
        identifier = identifier.strip()
        user = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(username=identifier).first()
        if user is None or not user.email:
            return AuthFlowResult(ok=True, message_key="auth_password_reset_requested")

        token = cls.create_token(user, "password_reset")
        reset_link = request.build_absolute_uri(reverse("reset_password", args=[token]))
        profile = cls.get_profile(user)
        context = cls._common_context(user, request, {"PasswordResetLink": reset_link, "VerificationLink": ""})
        try:
            cls.send_template_email("password_reset", [user.email], profile.preferred_language or lang or "en", context)
        except EmailDeliveryError:
            return AuthFlowResult(ok=False, error_key="auth_email_delivery_failed", user=user, profile=profile)
        cls.record_audit(user, "password_reset_requested")
        return AuthFlowResult(ok=True, message_key="auth_password_reset_requested", user=user, profile=profile)

    @classmethod
    def reset_password(cls, raw_token: str, password: str, confirm_password: str) -> AuthFlowResult:
        if not password:
            return AuthFlowResult(ok=False, error_key="auth_error_required_reset_password")
        if password != confirm_password:
            return AuthFlowResult(ok=False, error_key="auth_error_passwords_mismatch")

        token, error_key = cls.resolve_token(raw_token, "password_reset")
        if token is None:
            return AuthFlowResult(ok=False, error_key=error_key)

        try:
            validate_password(password, user=token.user)
        except ValidationError:
            return AuthFlowResult(ok=False, error_key="auth_error_password_validation")

        user = token.user
        user.set_password(password)
        user.save(update_fields=["password"])
        cls.mark_token_used(token)
        cls.record_audit(user, "password_reset_completed")
        return AuthFlowResult(ok=True, message_key="auth_password_reset_success", user=user, profile=cls.get_profile(user))

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
