"""Password reset request and completion workflow phases."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from core.authentication.serializers import AuthFlowResult
from core.authentication.emails import EmailDeliveryError

User = get_user_model()


class PasswordResetMixin:
    """Password reset request and completion."""

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
