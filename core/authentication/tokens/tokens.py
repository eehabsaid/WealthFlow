"""
Authentication token management utilities.
"""

import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from core.models import AuthToken

TOKEN_TTL = timedelta(hours=24)

def hash_token(raw_token: str) -> str:
    """Hashes raw token string using SHA256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_token(user, purpose: str, ttl: timedelta = TOKEN_TTL) -> str:
    """Generates a secure random token, invalidating existing usable tokens for the purpose."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    AuthToken.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
    ).update(used_at=timezone.now())
    AuthToken.objects.create(
        user=user,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=timezone.now() + ttl,
    )
    return raw_token

def resolve_token(raw_token: str, purpose: str) -> tuple[AuthToken | None, str]:
    """Resolves raw token string against databaseAuthToken."""
    token_hash = hash_token(raw_token)
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

def mark_token_used(token: AuthToken) -> None:
    """Marks the specified AuthToken as used."""
    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])
