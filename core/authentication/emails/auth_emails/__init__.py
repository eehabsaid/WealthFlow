"""Umbrella re-export for the Authentication Email domain, so both
core/authentication/emails/__init__.py and any other file can keep doing
`from core.authentication.emails.auth_emails import send_template_email`
unchanged, without needing to know these moved from a flat
core/authentication/emails/auth_emails.py into this package.

ORGANIZING PRINCIPLE: everything involved in composing and delivering
authentication-related transactional emails (welcome, verification,
approval, rejection, password reset) plus the ad-hoc SMTP test email.

STRUCTURE / CONVENTION:
  - templates_config.py   EMAIL_TEMPLATE_DEFINITIONS static table.
  - connection.py         build_mail_connection(), get_from_email(),
                           get_reply_to_emails().
  - body_builder.py       replace_placeholders(), build_email_bodies().
  - sender.py             EmailDeliveryError, send_template_email(),
                           send_smtp_test_email(), module logger.
  - If any file here grows past ~200 lines, split it by concern into
    more files in this same folder.
  - Always update this __init__.py's imports/__all__ to match.
"""

from core.authentication.emails.auth_emails.templates_config import (
    EMAIL_TEMPLATE_DEFINITIONS,
)
from core.authentication.emails.auth_emails.connection import (
    build_mail_connection,
    get_from_email,
    get_reply_to_emails,
)
from core.authentication.emails.auth_emails.body_builder import (
    replace_placeholders,
    build_email_bodies,
)
from core.authentication.emails.auth_emails.sender import (
    EmailDeliveryError,
    send_template_email,
    send_smtp_test_email,
)

__all__ = [
    "EMAIL_TEMPLATE_DEFINITIONS",
    "build_mail_connection",
    "get_from_email",
    "get_reply_to_emails",
    "replace_placeholders",
    "build_email_bodies",
    "EmailDeliveryError",
    "send_template_email",
    "send_smtp_test_email",
]
