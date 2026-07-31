"""
Authentication serializers and data structures.
"""

from dataclasses import dataclass
from core.models import UserProfile

@dataclass
class AuthFlowResult:
    ok: bool
    message_key: str = ""
    message_params: dict | None = None
    user: object | None = None
    profile: UserProfile | None = None
    error_key: str = ""
    extra: dict | None = None
