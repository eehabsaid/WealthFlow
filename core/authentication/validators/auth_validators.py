"""
Authentication validator utilities.
"""

import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def is_valid_username(username: str) -> bool:
    """Validates username syntax."""
    return bool(username and USERNAME_REGEX.match(username))

def is_valid_email(email: str) -> bool:
    """Validates basic email format."""
    return bool(email and EMAIL_REGEX.match(email.strip()))

def validate_user_password(password: str, user=None) -> list[str]:
    """
    Validates password against Django password validators.
    Returns list of error messages (empty if valid).
    """
    try:
        validate_password(password, user=user)
        return []
    except ValidationError as exc:
        return list(exc.messages)
