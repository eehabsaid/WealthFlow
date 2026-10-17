"""Stripe gateway (Checkout Sessions + signed webhooks + refunds).

Credentials come from AppSettings (Settings > Billing Plans > Payment Gateway),
secrets Fernet-encrypted like the Paymob and AI keys. Until both the secret key
and the webhook secret are saved, `is_configured()` is False and nothing here
touches the network. HTTP goes through `_stripe_http` so tests need no real keys.

NOTE: not exercised against the live Stripe API from the sandbox (no network
egress) -- verify end-to-end with Stripe test keys.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from core.models import AppSettings
from core.services.ai.credential_encryption import decrypt_credential, redact_secrets
from core.services.billing.gateway_base import GatewayError, PaymentGateway

logger = logging.getLogger(__name__)

STRIPE_API = "https://api.stripe.com/v1"
DEFAULT_CURRENCIES = "USD,EUR,GBP"
SIGNATURE_TOLERANCE_SECONDS = 300
ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
MERCHANT_PREFIX = "wf-inv-"


def minor_units(amount, currency_code: str) -> int:
    factor = 1 if str(currency_code).upper() in ZERO_DECIMAL else 100
    return int((Decimal(str(amount)) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _stripe_http(path: str, form: dict, secret: str, method: str = "POST") -> tuple[dict | None, int, str | None]:
    """One Stripe call (form-encoded, Bearer auth). Returns (json, status, error); error is secret-redacted."""
    data = urllib.parse.urlencode(form).encode("utf-8") if form else None
    req = urllib.request.Request(
        f"{STRIPE_API}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {secret}", "User-Agent": "WealthFlow/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}"), resp.status, None
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")[:300]
        except Exception:
            pass
        return None, exc.code, redact_secrets(f"HTTP {exc.code}: {body}", [secret])
    except urllib.error.URLError as exc:
        return None, 0, redact_secrets(f"URL Error: {exc.reason}", [secret])


class StripeGateway(PaymentGateway):
    name = "stripe"

    @staticmethod
    def get_config() -> dict:
        return {
            "secret_key": decrypt_credential(AppSettings.get("stripe_secret_key", "").strip()),
            "webhook_secret": decrypt_credential(AppSettings.get("stripe_webhook_secret", "").strip()),
        }

    @staticmethod
    def currencies() -> list:
        raw = AppSettings.get("stripe_currencies", DEFAULT_CURRENCIES) or DEFAULT_CURRENCIES
        return [c.strip().upper() for c in str(raw).replace(";", ",").split(",") if c.strip()]

    @classmethod
    def is_configured(cls, currency_code: str | None = None) -> bool:
        cfg = cls.get_config()
        if not (cfg["secret_key"] and cfg["webhook_secret"]):
            return False
        return currency_code is None or str(currency_code).upper() in cls.currencies()

    @classmethod
    def create_checkout(cls, *, invoice, user, return_base: str = "") -> dict:
        cfg = cls.get_config()
        code = invoice.currency.code
        if not cls.is_configured(code):
            raise GatewayError(f"Stripe is not configured for {code}.")
        base = str(return_base or "").rstrip("/")
        if not base:
            raise GatewayError("Stripe checkout needs the site address to return the customer to.")
        form = {
            "mode": "payment",
            "success_url": f"{base}/#billing-plans",
            "cancel_url": f"{base}/#billing-plans",
            "client_reference_id": f"{MERCHANT_PREFIX}{invoice.id}",
            "metadata[invoice_id]": str(invoice.id),
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": code.lower(),
            "line_items[0][price_data][unit_amount]": str(minor_units(invoice.amount, code)),
            "line_items[0][price_data][product_data][name]": f"WealthFlow {invoice.plan.name}",
        }
        if getattr(user, "email", ""):
            form["customer_email"] = user.email
        data, _status, err = _stripe_http("/checkout/sessions", form, cfg["secret_key"])
        if err or not data or not data.get("url") or not data.get("id"):
            raise GatewayError(f"Stripe checkout failed: {err or data}")
        return {"reference": data["id"], "redirect_url": data["url"]}

    @classmethod
    def verify_webhook(cls, body: bytes, signature_header: str, now: float | None = None) -> bool:
        """Stripe-Signature: t=<ts>,v1=<hmac>. HMAC-SHA256 over '<ts>.<raw body>' with the webhook secret."""
        secret = cls.get_config()["webhook_secret"]
        if not secret or not signature_header:
            return False
        parts = [p.split("=", 1) for p in signature_header.split(",") if "=" in p]
        stamps = [v for k, v in parts if k.strip() == "t"]
        sigs = [v for k, v in parts if k.strip() == "v1"]
        if not stamps or not sigs:
            return False
        try:
            stamp = int(stamps[0])
        except ValueError:
            return False
        if abs((now if now is not None else time.time()) - stamp) > SIGNATURE_TOLERANCE_SECONDS:
            return False
        expected = hmac.new(secret.encode("utf-8"), f"{stamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, s) for s in sigs)

    @classmethod
    def refund(cls, invoice, amount) -> dict:
        cfg = cls.get_config()
        if not cfg["secret_key"]:
            raise GatewayError("Stripe is not configured.")
        if not invoice.gateway_transaction_id:
            raise GatewayError("This invoice has no Stripe payment reference to refund.")
        form = {
            "payment_intent": invoice.gateway_transaction_id,
            "amount": str(minor_units(amount, invoice.currency.code)),
            "metadata[invoice_id]": str(invoice.id),
        }
        data, _status, err = _stripe_http("/refunds", form, cfg["secret_key"])
        if err or not data or data.get("status") not in ("succeeded", "pending"):
            raise GatewayError(f"Stripe refund failed: {err or (data or {}).get('failure_reason') or data}")
        return {"reference": data.get("id", ""), "status": data["status"]}
