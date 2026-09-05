"""
Template-driven email sending, SMTP test-email sending, and the shared
delivery error type.
"""

import logging
import smtplib
from django.conf import settings
from django.core.mail import get_connection
from core.models import AppSettings, EmailTemplate

from core.authentication.emails.auth_emails.connection import (
    build_mail_connection,
    get_from_email,
    get_reply_to_emails,
)
from core.authentication.emails.auth_emails.body_builder import (
    build_email_bodies,
    replace_placeholders,
)

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def send_template_email(template_key: str, to_emails: list[str], lang: str, context: dict) -> str:
    if not to_emails:
        return "skipped"
    from core.services.shared.email_template_service import EmailTemplateService
    from core.services.shared.auth_workflow_service import EmailMultiAlternatives
    EmailTemplateService.ensure_defaults()
    template = EmailTemplate.objects.get(key=template_key)
    subject = replace_placeholders(template.get_subject(lang), context)
    raw_body = replace_placeholders(template.get_body(lang), context)

    from_email = get_from_email()
    reply_to = get_reply_to_emails()
    plain_body, html_body = build_email_bodies(raw_body)
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
        connection=build_mail_connection(),
    )
    if html_body:
        message.attach_alternative(html_body, "text/html")

    try:
        message.send(fail_silently=False)
        logger.info("Successfully sent template email '%s' to %s via SMTP", template_key, to_emails)
        return "smtp"
    except Exception as exc:
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


def send_smtp_test_email(*, to_email: str) -> tuple[bool, str]:
    from core.services.shared.auth_workflow_service import EmailMultiAlternatives
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

    from_email = get_from_email()
    reply_to = get_reply_to_emails()
    plain_body, html_body = build_email_bodies(
        "SMTP is configured correctly. This is a test email from WealthFlow."
    )

    message = EmailMultiAlternatives(
        subject="WealthFlow SMTP test",
        body=plain_body,
        from_email=from_email,
        to=[to_email.strip()],
        reply_to=reply_to if reply_to else None,
        connection=build_mail_connection(),
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
