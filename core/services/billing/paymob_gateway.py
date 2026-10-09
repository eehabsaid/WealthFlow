"""Paymob (accept.paymob.com) payment gateway integration.

All credentials come from AppSettings (Settings > Billing Plans tab),
decrypted at call time — never hardcoded, never read from env vars or
settings.py. As long as any of them are missing, `is_configured()` is
False and CheckoutService falls back to fake/test-mode payments so
trial users aren't blocked while Ehab is setting this up.

NOTE: this talks to accept.paymob.com over the network. It has not been
exercised against the live Paymob API from this environment (sandboxed,
no network egress to paymob) — verify end-to-end once real keys are in.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from core.integrations.provider_utils import make_json_http_request
from core.models import AppSettings
from core.services.ai.credential_encryption import decrypt_credential, redact_secrets

logger = logging.getLogger(__name__)

PAYMOB_BASE_URL = "https://accept.paymob.com/api"

# Paymob accounts are regional (Egypt, KSA, UAE ... each has its own host,
# credentials, integration and iframe). The default credentials (Settings >
# Billing Plans) serve the currencies listed in AppSettings
# "paymob_default_currencies" (default: EGP). A currency with its own regional
# account stores it under paymob_cfg_<CODE>_<field>; those win over the default.
DEFAULT_CURRENCIES_FALLBACK = "EGP"
_REGION_FIELDS = ("api_key", "hmac_secret", "integration_id", "iframe_id", "base_url")
_REGION_SECRET_FIELDS = ("api_key", "hmac_secret")


def region_key(code: str, field: str) -> str:
    return f"paymob_cfg_{str(code).strip().upper()}_{field}"


def normalize_base_url(value: str) -> str:
    """Accepts 'ksa.paymob.com', 'https://ksa.paymob.com' or '.../api'; returns
    the https .../api base. Empty input means the default Egypt host."""
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return PAYMOB_BASE_URL
    if not raw.startswith("https://"):
        raw = "https://" + raw.split("://", 1)[-1]
    if not raw.endswith("/api"):
        raw += "/api"
    return raw

# Exact, alphabetically-ordered field list Paymob's webhook HMAC is
# computed over for "TRANSACTION" callbacks, per Paymob's documented
# HMAC calculation for the transaction processed callback.
_HMAC_FIELDS = (
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order.id",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
)


class PaymobConfigError(Exception):
    """Raised when a Paymob call is attempted without full configuration."""


class PaymobGateway:
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

    @classmethod
    def _auth_token(cls, cfg: dict) -> str:
        data, status, err = make_json_http_request(
            f"{cfg['base_url']}/auth/tokens",
            method="POST",
            payload={"api_key": cfg["api_key"]},
            secrets=[cfg["api_key"], cfg["hmac_secret"]],
        )
        if err or not data or "token" not in data:
            raise PaymobConfigError(redact_secrets(f"Paymob auth failed: {err or data}", [cfg["api_key"]]))
        return data["token"]

    @classmethod
    def test_connection(cls, currency_code: str) -> dict:
        """Authenticate against the SAVED regional account of `currency_code` (no order, no charge). Returns
        {ok, error_key, host, detail}: error_key is an i18n key for the Settings UI; detail is secret-redacted."""
        from urllib.parse import urlparse

        cfg = cls.get_region_config(currency_code)
        host = ""
        if cfg is None or not cfg.get("api_key"):
            return {"ok": False, "error_key": "paymob_test_not_configured", "host": host, "detail": ""}
        host = (urlparse(cfg["base_url"]).hostname or "").lower()
        if not (host == "paymob.com" or host.endswith(".paymob.com")):
            return {"ok": False, "error_key": "paymob_test_bad_host", "host": host, "detail": ""}
        try:
            cls._auth_token(cfg)
        except PaymobConfigError as exc:
            return {"ok": False, "error_key": "paymob_test_auth_failed", "host": host, "detail": str(exc)[:300]}
        return {"ok": True, "error_key": "paymob_test_ok", "host": host, "detail": ""}

    @classmethod
    def _create_order(cls, cfg: dict, auth_token: str, amount_cents: int, currency_code: str, merchant_order_id: str) -> int:
        data, status, err = make_json_http_request(
            f"{cfg['base_url']}/ecommerce/orders",
            method="POST",
            payload={
                "auth_token": auth_token,
                "delivery_needed": False,
                "amount_cents": amount_cents,
                "currency": currency_code,
                "merchant_order_id": merchant_order_id,
                "items": [],
            },
        )
        if err or not data or "id" not in data:
            raise PaymobConfigError(f"Paymob order creation failed: {err or data}")
        return data["id"]

    @classmethod
    def _create_payment_key(cls, auth_token: str, cfg: dict, order_id: int, amount_cents: int, currency_code: str, billing_data: dict) -> str:
        data, status, err = make_json_http_request(
            f"{cfg['base_url']}/acceptance/payment_keys",
            method="POST",
            payload={
                "auth_token": auth_token,
                "amount_cents": amount_cents,
                "expiration": 3600,
                "order_id": order_id,
                "billing_data": billing_data,
                "currency": currency_code,
                "integration_id": cfg["integration_id"],
            },
        )
        if err or not data or "token" not in data:
            raise PaymobConfigError(f"Paymob payment key request failed: {err or data}")
        return data["token"]

    @classmethod
    def create_checkout(cls, *, amount_cents: int, currency_code: str, merchant_order_id: str, billing_data: dict) -> dict:
        """Runs the full auth -> order -> payment key flow and returns the
        iframe URL to redirect the customer to, plus the Paymob order id
        (stored on Invoice.gateway_reference for webhook correlation)."""
        cfg = cls.get_config(currency_code)
        if not cls._complete(cfg):
            raise PaymobConfigError(f"Paymob is not configured for {currency_code}.")

        auth_token = cls._auth_token(cfg)
        order_id = cls._create_order(cfg, auth_token, amount_cents, currency_code, merchant_order_id)
        payment_token = cls._create_payment_key(auth_token, cfg, order_id, amount_cents, currency_code, billing_data)
        host = cfg["base_url"][: -len("/api")]
        iframe_url = f"{host}/api/acceptance/iframes/{cfg['iframe_id']}?payment_token={payment_token}"
        return {"order_id": order_id, "iframe_url": iframe_url}

    @classmethod
    def verify_webhook_hmac(cls, payload: dict, received_hmac: str) -> bool:
        """Verifies a Paymob transaction-callback webhook's `hmac` query
        param against the transaction object in the POST body, per
        Paymob's documented field order (see _HMAC_FIELDS)."""
        secrets = cls.all_hmac_secrets()
        if not secrets or not received_hmac:
            return False

        obj = payload.get("obj", payload)
        try:
            parts = []
            for field in _HMAC_FIELDS:
                node = obj
                for segment in field.split("."):
                    node = (node or {}).get(segment) if isinstance(node, dict) else None
                parts.append("" if node is None else str(node).lower() if isinstance(node, bool) else str(node))
            concatenated = "".join(parts)
        except Exception as exc:
            logger.warning("Paymob webhook HMAC field extraction failed: %s", exc)
            return False

        for secret in secrets:
            computed = hmac.new(secret.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha512).hexdigest()
            if hmac.compare_digest(computed, received_hmac):
                return True
        return False
