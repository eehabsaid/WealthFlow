"""
Centralized AI Credential Encryption Utility.

Provides symmetric encryption at rest for AI provider API keys using cryptography's Fernet.
Derives encryption key from WEALTHFLOW_AI_ENCRYPTION_KEY environment variable or falls back
to SHA256-derived key from Django's SECRET_KEY.
Prefixes encrypted values with 'enc:'.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Sequence

from cryptography.fernet import Fernet
from django.conf import settings

logger = logging.getLogger(__name__)

ENC_PREFIX = "enc:"
MASK_SYMBOL = "••••"


def get_fernet_key() -> bytes:
    """
    Returns 32-byte urlsafe base64 key for Fernet encryption.
    Uses WEALTHFLOW_AI_ENCRYPTION_KEY env var if defined, otherwise derives key
    from Django's SECRET_KEY.
    """
    env_key = os.environ.get("WEALTHFLOW_AI_ENCRYPTION_KEY", "").strip()
    if env_key:
        try:
            # Check if valid 32-byte urlsafe base64 Fernet key
            key_bytes = env_key.encode("utf-8")
            if len(base64.urlsafe_b64decode(key_bytes)) == 32:
                return key_bytes
        except Exception:
            pass
        # Fallback to deriving SHA256 key from env_key string
        return base64.urlsafe_b64encode(hashlib.sha256(env_key.encode("utf-8")).digest())

    secret_key = str(getattr(settings, "SECRET_KEY", "wealthflow_default_fallback_secret_key")).encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(secret_key).digest())


def is_encrypted(value: str | None) -> bool:
    """Returns True if value starts with 'enc:'."""
    if not value or not isinstance(value, str):
        return False
    return value.startswith(ENC_PREFIX)


def is_masked(value: str | None) -> bool:
    """Returns True if value contains the masking symbol '••••'."""
    if not value or not isinstance(value, str):
        return False
    return MASK_SYMBOL in value


def encrypt_credential(plaintext: str | None) -> str:
    """
    Encrypts a plaintext string using Fernet and returns 'enc:<ciphertext>'.
    Returns empty string if input is empty.
    Returns value unchanged if already encrypted or masked.
    """
    if not plaintext or not isinstance(plaintext, str):
        return ""
    clean = plaintext.strip()
    if not clean or is_encrypted(clean) or is_masked(clean):
        return clean

    f = Fernet(get_fernet_key())
    ciphertext = f.encrypt(clean.encode("utf-8")).decode("utf-8")
    return f"{ENC_PREFIX}{ciphertext}"


def decrypt_credential(ciphertext: str | None) -> str:
    """
    Decrypts an 'enc:<ciphertext>' string to plaintext.
    If value is unencrypted legacy text, returns as is.
    If decryption fails (e.g. key changed), logs warning and returns empty string.
    """
    if not ciphertext or not isinstance(ciphertext, str):
        return ""
    clean = ciphertext.strip()
    if not clean:
        return ""
    if not is_encrypted(clean):
        return clean

    token = clean[len(ENC_PREFIX):]
    try:
        f = Fernet(get_fernet_key())
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.warning("Failed to decrypt AI credential setting (encryption key may have changed): %s", exc)
        return ""


def mask_credential(plaintext: str | None) -> str:
    """
    Returns masked version of plaintext credential for safe UI display (e.g. '••••1a2b').
    Never exposes raw plaintext.
    """
    if not plaintext or not isinstance(plaintext, str):
        return ""
    clean = plaintext.strip()
    if not clean:
        return ""
    if is_masked(clean):
        return clean
    if len(clean) <= 4:
        return MASK_SYMBOL
    return f"{MASK_SYMBOL}{clean[-4:]}"


def redact_secrets(text: str | None, secrets: Sequence[str | None] | None = None) -> str:
    """
    Strips raw secrets / API keys from log messages or exception text.
    """
    if text is None:
        return ""
    s_text = str(text)
    if not secrets:
        return s_text

    for s in secrets:
        if s and isinstance(s, str):
            clean_s = s.strip()
            if len(clean_s) >= 3:
                s_text = s_text.replace(clean_s, "[REDACTED]")
    return s_text
