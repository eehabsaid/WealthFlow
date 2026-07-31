"""
Authentication email delivery logic.
"""

import logging
import re
import smtplib
from email.utils import formataddr
from django.conf import settings
from django.core.mail import get_connection
from core.models import AppSettings, EmailTemplate

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

class EmailDeliveryError(Exception):
    pass

def replace_placeholders(text: str, context: dict) -> str:
    out = str(text or "")
    for key, value in (context or {}).items():
        out = out.replace(f"{{{{{key}}}}}", str(value or ""))
    return out

def build_mail_connection():
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

def get_from_email() -> str:
    sender = AppSettings.get("sender_email", "").strip()
    smtp_user = AppSettings.get("smtp_username", "").strip()
    default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "").strip()

    from_address = smtp_user or sender or default_from or "noreply@wealthflow.local"
    if "<" in from_address and ">" in from_address:
        return from_address
    return formataddr(("WealthFlow", from_address))

def get_reply_to_emails() -> list[str]:
    sender = AppSettings.get("sender_email", "").strip()
    smtp_user = AppSettings.get("smtp_username", "").strip()
    if sender and "@" in sender and sender.lower() != smtp_user.lower():
        if "<" in sender and ">" in sender:
            sender = sender.split("<")[1].split(">")[0].strip()
        return [sender]
    return []

def build_email_bodies(raw_body: str) -> tuple[str, str]:
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
