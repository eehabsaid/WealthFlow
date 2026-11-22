"""Paymob configuration lookups (default and regional accounts)."""

from __future__ import annotations


from core.models import AppSettings
from ai.services.credential_encryption import decrypt_credential
from .paymob_gateway_helpers import DEFAULT_CURRENCIES_FALLBACK, PAYMOB_BASE_URL, _REGION_FIELDS, _REGION_SECRET_FIELDS, normalize_base_url, region_key


class _PaymobConfigMixin:
    @staticmethod
    def default_currencies() -> list:
        raw = AppSettings.get("paymob_default_currencies", DEFAULT_CURRENCIES_FALLBACK) or DEFAULT_CURRENCIES_FALLBACK
        return [c.strip().upper() for c in str(raw).replace(";", ",").split(",") if c.strip()]

    @staticmethod
    def get_default_config() -> dict:
        return {
            "api_key": decrypt_credential(AppSettings.get("paymob_api_key", "").strip()),
            "hmac_secret": decrypt_credential(AppSettings.get("paymob_hmac_secret", "").strip()),
            "integration_id": AppSettings.get("paymob_integration_id", "").strip(),
            "iframe_id": AppSettings.get("paymob_iframe_id", "").strip(),
            "base_url": PAYMOB_BASE_URL,
        }

    @staticmethod
    def get_region_config(currency_code: str) -> dict | None:
        """The regional account for one currency, or None if none is stored."""
        cfg = {}
        for field in _REGION_FIELDS:
            raw = AppSettings.get(region_key(currency_code, field), "").strip()
            cfg[field] = decrypt_credential(raw) if field in _REGION_SECRET_FIELDS else raw
        if not any(cfg.values()):
            return None
        cfg["base_url"] = normalize_base_url(cfg["base_url"])
        return cfg

    @classmethod
    def get_config(cls, currency_code: str | None = None) -> dict:
        """Credentials used for `currency_code`. Without a code (legacy callers)
        this is the default account. A currency with a regional account always
        uses it; otherwise the default account is used only for the currencies
        it serves — any other currency gets an empty config (not configured)."""
        if not currency_code:
            return cls.get_default_config()
        region = cls.get_region_config(currency_code)
        if region is not None:
            return region
        if str(currency_code).strip().upper() in cls.default_currencies():
            return cls.get_default_config()
        return {**cls.get_default_config(), "api_key": "", "hmac_secret": "", "integration_id": "", "iframe_id": ""}

    @staticmethod
    def _complete(cfg: dict) -> bool:
        return bool(cfg["api_key"] and cfg["hmac_secret"] and cfg["integration_id"] and cfg["iframe_id"])

    @classmethod
    def is_configured(cls, currency_code: str | None = None) -> bool:
        """Without a code: is the default account complete? With a code: can
        this currency be charged through a real Paymob account?"""
        return cls._complete(cls.get_config(currency_code))

    @classmethod
    def any_configured(cls) -> bool:
        """True once ANY account (default or regional) is complete. This is what
        switches fake/test-mode payments off, so they can never bypass a real
        gateway for some currencies."""
        if cls.is_configured():
            return True
        from core.models import Currency

        codes = set(Currency.objects.filter(owner=None).values_list("code", flat=True))
        return any((cfg := cls.get_region_config(c)) is not None and cls._complete(cfg) for c in codes)

    @classmethod
    def all_hmac_secrets(cls) -> list:
        """Every configured webhook secret (default + regional), for signature checks."""
        from core.models import Currency

        secrets = [cls.get_default_config()["hmac_secret"]]
        for code in Currency.objects.filter(owner=None).values_list("code", flat=True):
            cfg = cls.get_region_config(code)
            if cfg:
                secrets.append(cfg["hmac_secret"])
        return [x for i, x in enumerate(secrets) if x and x not in secrets[:i]]
