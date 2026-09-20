"""Registration, login-block resolution, and email verification workflow phases."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.models import AppSettings
from core.authentication.serializers import AuthFlowResult
from core.authentication.emails import EmailDeliveryError
from core.authentication.services.member_role import assign_member_role
from core.services.billing import SubscriptionService


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
            # Same response as a fresh signup so the form cannot be used to
            # discover which emails are registered; the real owner is told
            # by email instead.
            cls._notify_existing_account(request, existing_user, lang)
            return AuthFlowResult(ok=True, message_key="auth_signup_success_verify_email")

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

        return AuthFlowResult(ok=True, message_key="auth_signup_success_verify_email", user=user, profile=profile)

    @classmethod
    def _notify_existing_account(cls, request, user, lang):
        """Email the owner of an already-registered address (never reveals it to the caller)."""
        profile = cls.get_profile(user)
        try:
            if profile.account_status == "pending_email_verification":
                token = cls.create_token(user, "email_verification")
                link = request.build_absolute_uri(reverse("verify_email", args=[token]))
                context = cls._common_context(user, request, {"VerificationLink": link, "PasswordResetLink": ""})
                cls.send_template_email("email_verification", [user.email], profile.preferred_language or lang, context)
            elif profile.account_status == "active":
                cls.request_password_reset(request, identifier=user.email, lang=lang)
        except EmailDeliveryError:
            pass

    @classmethod
    def get_login_block(cls, user) -> str:
        if user is None:
            return "auth_error_invalid_login"
        profile = cls.get_profile(user)
        if not profile.email_verified:
            return "auth_status_verify_email"
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
        with transaction.atomic():
            profile.email_verified = True
            profile.account_status = "active"
            profile.approved_at = timezone.now()
            profile.preferred_language = profile.preferred_language or AppSettings.get("active_language", "en") or "en"
            profile.save()
            user.is_active = True
            user.save(update_fields=["is_active"])
            assign_member_role(user)
            SubscriptionService.start_trial(user)
            cls.mark_token_used(token)
            cls.record_audit(user, "email_verified", details="active")

        context = cls._common_context(user, request, {"VerificationLink": "", "PasswordResetLink": ""})
        try:
            cls.send_template_email("welcome_email", [user.email], profile.preferred_language or "en", context)
        except EmailDeliveryError:
            cls.record_audit(user, "email_verified", details="welcome_email_failed")

        return AuthFlowResult(ok=True, message_key="auth_verify_success", user=user, profile=profile)
