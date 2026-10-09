"""Re-encrypt every stored 'enc:' credential (AI provider keys, Paymob secrets, per-user keys) under the current key.

Used by `manage.py rekey_ai_keys` after setting a private WEALTHFLOW_AI_ENCRYPTION_KEY. A row is only rewritten when it
decrypts with the OLD key; rows that already decrypt with the current key are left alone, and rows neither key can read
are reported and never touched."""

from __future__ import annotations

from cryptography.fernet import Fernet

from core.models import AppSettings
from core.services.ai.credential_encryption import ENC_PREFIX, fernet_key_from_secret, get_fernet_key, settings_secret_key


def _decrypt(key: bytes, value: str):
    try:
        return Fernet(key).decrypt(value[len(ENC_PREFIX):].encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def rekey_all(old_secret: str | None = None, apply: bool = False) -> dict:
    """old_secret=None means the SECRET_KEY-derived fallback key. Returns counts and the unreadable setting keys."""
    old_key = fernet_key_from_secret(old_secret) if old_secret else settings_secret_key()
    new_key = get_fernet_key()
    result = {"rewritten": 0, "already_current": 0, "unreadable": [], "same_key": old_key == new_key, "applied": apply}
    if result["same_key"]:
        return result
    new_fernet = Fernet(new_key)
    for row in AppSettings.objects.filter(value__startswith=ENC_PREFIX):
        if _decrypt(new_key, row.value) is not None:
            result["already_current"] += 1
            continue
        plain = _decrypt(old_key, row.value)
        if plain is None:
            result["unreadable"].append(row.key if row.owner_id is None else f"{row.key} (user {row.owner_id})")
            continue
        if apply:
            row.value = ENC_PREFIX + new_fernet.encrypt(plain.encode("utf-8")).decode("utf-8")
            row.save(update_fields=["value"])
        result["rewritten"] += 1
    return result
