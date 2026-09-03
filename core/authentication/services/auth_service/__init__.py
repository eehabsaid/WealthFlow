"""
Core authentication workflow service implementation.

Sibling modules:
- constants.py: PROFILE_STATUS_ERROR_KEYS
- shared_mixin.py: AuthSharedMixin (profile lookup, token/audit/email delegation)
- registration_mixin.py: RegistrationMixin (register_user, get_login_block, verify_email)
- password_reset_mixin.py: PasswordResetMixin (request_password_reset, reset_password)
- account_status_mixin.py: AccountStatusMixin (approve_user, reject_user, disable_user, enable_user)
"""

import logging
from datetime import timedelta

from core.authentication.serializers import AuthFlowResult
from core.authentication.emails import EmailDeliveryError

from .constants import PROFILE_STATUS_ERROR_KEYS
from .shared_mixin import AuthSharedMixin
from .registration_mixin import RegistrationMixin
from .password_reset_mixin import PasswordResetMixin
from .account_status_mixin import AccountStatusMixin

logger = logging.getLogger(__name__)

__all__ = [
    "AuthWorkflowService",
    "PROFILE_STATUS_ERROR_KEYS",
    "AuthFlowResult",
    "EmailDeliveryError",
]


class AuthWorkflowService(
    RegistrationMixin,
    PasswordResetMixin,
    AccountStatusMixin,
    AuthSharedMixin,
):
    token_ttl = timedelta(hours=24)
