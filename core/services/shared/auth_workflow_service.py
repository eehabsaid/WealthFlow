"""
Backward compatibility shim for core.services.shared.auth_workflow_service.
Re-exports AuthWorkflowService, AuthFlowResult, and EmailDeliveryError from core.authentication.services.
"""

from django.core.mail import EmailMultiAlternatives
from core.authentication.services import (
    AuthWorkflowService,
    AuthFlowResult,
    EmailDeliveryError,
    PROFILE_STATUS_ERROR_KEYS,
)
from core.services.shared.email_template_service import EmailTemplateService
from core.authentication.emails import (
    EMAIL_TEMPLATE_DEFINITIONS,
    send_template_email,
    send_smtp_test_email,
    replace_placeholders,
    get_from_email,
    get_reply_to_emails,
    build_email_bodies,
)
from core.authentication.tokens import (
    hash_token,
    create_token,
    resolve_token,
    mark_token_used,
)

__all__ = [
    "AuthWorkflowService",
    "AuthFlowResult",
    "EmailDeliveryError",
    "PROFILE_STATUS_ERROR_KEYS",
    "EmailTemplateService",
    "EMAIL_TEMPLATE_DEFINITIONS",
    "EmailMultiAlternatives",
    "send_template_email",
    "send_smtp_test_email",
    "replace_placeholders",
    "get_from_email",
    "get_reply_to_emails",
    "build_email_bodies",
    "hash_token",
    "create_token",
    "resolve_token",
    "mark_token_used",
]