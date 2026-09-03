"""Shared helpers: profile lookup, token/audit delegation, email context building."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import AppSettings, UserProfile
from core.authentication.tokens import (
    create_token,
    resolve_token,
    mark_token_used,
    hash_token,
)
from core.authentication.emails import send_template_email, send_smtp_test_email, replace_placeholders
from core.authentication.utils import record_audit

User = get_user_model()


class AuthSharedMixin:
    """Common helpers used by all auth workflow phases."""

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
