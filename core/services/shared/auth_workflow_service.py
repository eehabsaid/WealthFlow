from email.utils import formataddr
import hashlib
import logging
import re
import secrets
import smtplib
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.models import AppSettings, AuthAuditLog, AuthToken, EmailTemplate, UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)

EMAIL_TEMPLATE_DEFINITIONS = [
    {
        "key": "welcome_email",
        "subject_key": "email_template_welcome_subject",
        "body_key": "email_template_welcome_body",
        "description_key": "email_template_welcome_desc",
    },
    {
        "key": "email_verification",
        "subject_key": "email_template_verification_subject",
        "body_key": "email_template_verification_body",
        "description_key": "email_template_verification_desc",
    },
    {
        "key": "admin_approval_request",
        "subject_key": "email_template_admin_approval_subject",
        "body_key": "email_template_admin_approval_body",
        "description_key": "email_template_admin_approval_desc",
    },
    {
        "key": "account_approved",
        "subject_key": "email_template_account_approved_subject",
        "body_key": "email_template_account_approved_body",
        "description_key": "email_template_account_approved_desc",
    },
    {
        "key": "account_rejected",
        "subject_key": "email_template_account_rejected_subject",
        "body_key": "email_template_account_rejected_body",
        "description_key": "email_template_account_rejected_desc",
    },
    {
        "key": "password_reset",
        "subject_key": "email_template_password_reset_subject",
        "body_key": "email_template_password_reset_body",
        "description_key": "email_template_password_reset_desc",
    },
]

PROFILE_STATUS_ERROR_KEYS = {
    "pending_email_verification": "auth_status_verify_email",
    "pending_admin_approval": "auth_status_pending_admin_approval",
    "rejected": "auth_status_rejected",
    "disabled": "auth_status_disabled",
}

@dataclass
class AuthFlowResult:
    ok: bool
    message_key: str = ""
    message_params: dict | None = None
    user: object | None = None
    profile: UserProfile | None = None
    error_key: str = ""
    extra: dict | None = None

from core.services.shared.email_template_service import EmailTemplateService

class EmailDeliveryError(Exception):
    pass

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
        out = str(text or "")
        for key, value in (context or {}).items():
            out = out.replace(f"{{{{{key}}}}}", str(value or ""))
        return out

    @classmethod
    def _hash_token(cls, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def create_token(cls, user, purpose: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = cls._hash_token(raw_token)
        AuthToken.objects.filter(
            user=user,
            purpose=purpose,
            used_at__isnull=True,
        ).update(used_at=timezone.now())
        AuthToken.objects.create(
            user=user,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=timezone.now() + cls.token_ttl,
        )
        return raw_token

    @classmethod
    def resolve_token(cls, raw_token: str, purpose: str) -> tuple[AuthToken | None, str]:
        token_hash = cls._hash_token(raw_token)
        try:
            token = AuthToken.objects.select_related("user").get(
                token_hash=token_hash,
                purpose=purpose,
            )
        except AuthToken.DoesNotExist:
            return None, "auth_token_invalid"
        if token.used_at is not None:
            return None, "auth_token_used"
        if token.is_expired():
            return None, "auth_token_expired"
        return token, ""

    @classmethod
    def mark_token_used(cls, token: AuthToken) -> None:
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])

    @classmethod
    def record_audit(cls, user, event_type: str, actor=None, details: str = "") -> None:
        AuthAuditLog.objects.create(user=user, actor=actor, event_type=event_type, details=details)

    @classmethod
    def _build_mail_connection(cls):
        host = AppSettings.get("smtp_host", "")
        port = int(AppSettings.get("smtp_port", 0) or 0)
        username = AppSettings.get("smtp_username", "")
        password = AppSettings.get("smtp_password", "")
        use_tls = str(AppSettings.get("smtp_use_tls", "false")).lower() == "true"
        use_ssl = str(AppSettings.get("smtp_use_ssl", "false")).lower() == "true"

        kwargs = {}
        if host:
            kwargs["host"] = host
        if port:
            kwargs["port"] = port
        if username:
            kwargs["username"] = username
        if password:
            kwargs["password"] = password
        if kwargs:
            kwargs["use_tls"] = use_tls
            kwargs["use_ssl"] = use_ssl
        return get_connection(**kwargs)

    @classmethod
    def _from_email(cls) -> str:
        sender = AppSettings.get("sender_email", "").strip()
        smtp_user = AppSettings.get("smtp_username", "").strip()
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "").strip()

        from_address = smtp_user or sender or default_from or "noreply@wealthflow.local"
        if "<" in from_address and ">" in from_address:
            return from_address
        return formataddr(("WealthFlow", from_address))

    @classmethod
    def _reply_to_emails(cls) -> list[str]:
        sender = AppSettings.get("sender_email", "").strip()
        smtp_user = AppSettings.get("smtp_username", "").strip()
        if sender and "@" in sender and sender.lower() != smtp_user.lower():
            if "<" in sender and ">" in sender:
                sender = sender.split("<")[1].split(">")[0].strip()
            return [sender]
        return []

    @classmethod
    def _build_email_bodies(cls, raw_body: str) -> tuple[str, str]:
        text = str(raw_body or "").strip()
        has_html_tags = bool(re.search(r"<(html|body|div|p|a|br|table|span)[^>]*>", text, re.IGNORECASE))

        if has_html_tags:
            html_body = text
            plain_body = re.sub(r"<[^>]+>", "", text).strip()
        else:
            plain_body = text
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            html_parts = []

            for p in paragraphs:
                formatted_p = p.replace("\n", "<br>")
                url_match = re.search(r"https?://[^\s<]+", formatted_p)
                if url_match:
                    url = url_match.group(0)
                    button_html = (
                        f'<div style="margin: 16px 0;">'
                        f'<a href="{url}" target="_blank" style="background-color: #1a6ef5; color: #ffffff; '
                        f'padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; '
                        f'display: inline-block;">Confirm / Verify</a>'
                        f'</div>'
                        f'<p style="font-size: 12px; color: #666666;">Or copy and paste this link into your browser:<br>'
                        f'<a href="{url}" style="color: #1a6ef5; word-break: break-all;">{url}</a></p>'
                    )
                    formatted_p = re.sub(r"https?://[^\s<]+", button_html, formatted_p, count=1)

                html_parts.append(f'<p style="margin: 0 0 16px 0;">{formatted_p}</p>')

            content_html = "\n".join(html_parts)

            html_body = (
                f'<!DOCTYPE html>'
                f'<html>'
                f'<head><meta charset="utf-8"></head>'
                f'<body style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; '
                f'font-size: 15px; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">'
                f'<div style="max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; '
                f'border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">'
                f'{content_html}'
                f'</div>'
                f'</body>'
                f'</html>'
            )

        return plain_body, html_body

    @classmethod
    def send_template_email(cls, template_key: str, to_emails: list[str], lang: str, context: dict) -> str:
        if not to_emails:
            return "skipped"
        EmailTemplateService.ensure_defaults()
        template = EmailTemplate.objects.get(key=template_key)
        subject = cls.replace_placeholders(template.get_subject(lang), context)
        raw_body = cls.replace_placeholders(template.get_body(lang), context)

        from_email = cls._from_email()
        reply_to = cls._reply_to_emails()
        plain_body, html_body = cls._build_email_bodies(raw_body)
        extra_headers = {
            "Auto-Submitted": "auto-generated",
            "X-Auto-Response-Suppress": "All",
        }

        message = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=from_email,
            to=to_emails,
            reply_to=reply_to if reply_to else None,
            headers=extra_headers,
            connection=cls._build_mail_connection(),
        )
        if html_body:
            message.attach_alternative(html_body, "text/html")

        try:
            message.send(fail_silently=False)
            logger.info("Successfully sent template email '%s' to %s via SMTP", template_key, to_emails)
            return "smtp"
        except Exception as exc:
            # Authentication and connectivity failures are expected in many local/dev setups.
            # Log concise diagnostics without traceback noise or dumping message bodies.
            logger.info(
                "Email delivery failed for template %s (%s: %s)",
                template_key,
                exc.__class__.__name__,
                str(exc),
            )
            allow_console_fallback = (
                str(AppSettings.get("email_console_fallback", "false")).lower() == "true"
            )
            if settings.DEBUG and allow_console_fallback:
                console_message = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=from_email,
                    to=to_emails,
                    reply_to=reply_to if reply_to else None,
                    connection=get_connection("django.core.mail.backends.console.EmailBackend"),
                )
                if html_body:
                    console_message.attach_alternative(html_body, "text/html")
                console_message.send(fail_silently=True)
                return "console_fallback"

            if isinstance(exc, smtplib.SMTPAuthenticationError):
                raise EmailDeliveryError("smtp_authentication_failed") from exc
            raise EmailDeliveryError(str(exc)) from exc

    @classmethod
    def send_smtp_test_email(cls, *, to_email: str) -> tuple[bool, str]:
        required = {
            "sender_email": AppSettings.get("sender_email", "").strip(),
            "smtp_host": AppSettings.get("smtp_host", "").strip(),
            "smtp_port": AppSettings.get("smtp_port", "").strip(),
            "smtp_username": AppSettings.get("smtp_username", "").strip(),
            "smtp_password": AppSettings.get("smtp_password", "").strip(),
        }
        if not to_email.strip():
            return False, "smtp_test_error_recipient_required"
        if any(not value for value in required.values()):
            return False, "smtp_test_error_incomplete_settings"

        from_email = cls._from_email()
        reply_to = cls._reply_to_emails()
        plain_body, html_body = cls._build_email_bodies(
            "SMTP is configured correctly. This is a test email from WealthFlow."
        )

        message = EmailMultiAlternatives(
            subject="WealthFlow SMTP test",
            body=plain_body,
            from_email=from_email,
            to=[to_email.strip()],
            reply_to=reply_to if reply_to else None,
            connection=cls._build_mail_connection(),
        )
        if html_body:
            message.attach_alternative(html_body, "text/html")

        try:
            message.send(fail_silently=False)
            return True, "smtp_test_success"
        except Exception as exc:
            logger.info(
                "SMTP test failed (%s: %s)",
                exc.__class__.__name__,
                str(exc),
            )
            if isinstance(exc, smtplib.SMTPAuthenticationError):
                reason = str(exc).lower()
                if "5.7.139" in reason or "basic authentication is disabled" in reason:
                    return False, "smtp_test_error_basic_auth_disabled"
                return False, "smtp_test_error_auth"
            return False, "smtp_test_error_generic"

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

        # Welcome email is non-critical. If it fails, keep the registration flow intact
        # as long as the verification email was sent successfully.
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