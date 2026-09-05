"""
SMTP connection construction and from/reply-to address resolution.
"""

from email.utils import formataddr
from django.conf import settings
from django.core.mail import get_connection
from core.models import AppSettings


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
