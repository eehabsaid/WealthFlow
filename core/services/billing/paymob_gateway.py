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
from ai.services.credential_encryption import redact_secrets
from .paymob_gateway_config import _PaymobConfigMixin  # noqa: F401
from .paymob_gateway_helpers import PaymobConfigError, _HMAC_FIELDS, PAYMOB_BASE_URL, DEFAULT_CURRENCIES_FALLBACK, _REGION_FIELDS, _REGION_SECRET_FIELDS, region_key, normalize_base_url  # noqa: F401


logger = logging.getLogger(__name__)


class PaymobGateway(_PaymobConfigMixin):
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
