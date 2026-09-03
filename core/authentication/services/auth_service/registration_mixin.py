"""Registration, login-block resolution, and email verification workflow phases."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse

from core.models import AppSettings
from core.authentication.serializers import AuthFlowResult
from core.authentication.emails import EmailDeliveryError

from .constants import PROFILE_STATUS_ERROR_KEYS

User = get_user_model()


class RegistrationMixin:
    """User registration, login-block resolution, and email verification."""

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
