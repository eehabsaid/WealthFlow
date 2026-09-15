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
    def get_config() -> dict:
        return {
            "api_key": decrypt_credential(AppSettings.get("paymob_api_key", "").strip()),
            "hmac_secret": decrypt_credential(AppSettings.get("paymob_hmac_secret", "").strip()),
            "integration_id": AppSettings.get("paymob_integration_id", "").strip(),
            "iframe_id": AppSettings.get("paymob_iframe_id", "").strip(),
        }

    @classmethod
    def is_configured(cls) -> bool:
        cfg = cls.get_config()
        return bool(cfg["api_key"] and cfg["hmac_secret"] and cfg["integration_id"] and cfg["iframe_id"])

    @classmethod
    def _auth_token(cls, cfg: dict) -> str:
        data, status, err = make_json_http_request(
            f"{PAYMOB_BASE_URL}/auth/tokens",
            method="POST",
            payload={"api_key": cfg["api_key"]},
            secrets=[cfg["api_key"], cfg["hmac_secret"]],
        )
        if err or not data or "token" not in data:
            raise PaymobConfigError(redact_secrets(f"Paymob auth failed: {err or data}", [cfg["api_key"]]))
        return data["token"]

    @classmethod
    def _create_order(cls, auth_token: str, amount_cents: int, currency_code: str, merchant_order_id: str) -> int:
        data, status, err = make_json_http_request(
            f"{PAYMOB_BASE_URL}/ecommerce/orders",
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
            f"{PAYMOB_BASE_URL}/acceptance/payment_keys",
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
        cfg = cls.get_config()
        if not cls.is_configured():
            raise PaymobConfigError("Paymob is not fully configured.")

        auth_token = cls._auth_token(cfg)
        order_id = cls._create_order(auth_token, amount_cents, currency_code, merchant_order_id)
        payment_token = cls._create_payment_key(auth_token, cfg, order_id, amount_cents, currency_code, billing_data)
        iframe_url = f"{PAYMOB_BASE_URL.replace('/api', '')}/api/acceptance/iframes/{cfg['iframe_id']}?payment_token={payment_token}"
        return {"order_id": order_id, "iframe_url": iframe_url}

    @classmethod
    def verify_webhook_hmac(cls, payload: dict, received_hmac: str) -> bool:
        """Verifies a Paymob transaction-callback webhook's `hmac` query
        param against the transaction object in the POST body, per
        Paymob's documented field order (see _HMAC_FIELDS)."""
        cfg = cls.get_config()
        if not cfg["hmac_secret"] or not received_hmac:
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

        computed = hmac.new(
            cfg["hmac_secret"].encode("utf-8"),
            concatenated.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(computed, received_hmac)
