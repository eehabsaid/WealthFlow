"""Paymob refund call (void_refund/refund), split from paymob_gateway.py to stay small.

NOTE: not exercised against the live Paymob API from the sandbox -- verify with
a real (test-integration) transaction before relying on it.
"""

from __future__ import annotations

from core.integrations.provider_utils import make_json_http_request
from core.services.billing.gateway_base import GatewayError
from core.services.billing.paymob_gateway import PaymobConfigError, PaymobGateway


def _truthy(value) -> bool:
    return value is True or str(value).strip().lower() == "true"


def paymob_refund(invoice, amount) -> dict:
    code = invoice.currency.code
    cfg = PaymobGateway.get_config(code)
    if not PaymobGateway._complete(cfg):
        raise GatewayError(f"Paymob is not configured for {code}.")
    if not invoice.gateway_transaction_id:
        raise GatewayError("This invoice has no Paymob transaction id to refund (paid before refunds were supported).")
    try:
        token = PaymobGateway._auth_token(cfg)
    except PaymobConfigError as exc:
        raise GatewayError(str(exc)) from exc
    from core.services.billing.checkout_helpers import amount_to_cents

    data, _status, err = make_json_http_request(
        f"{cfg['base_url']}/acceptance/void_refund/refund",
        method="POST",
        headers={"Authorization": f"Bearer {token}"},
        payload={"transaction_id": invoice.gateway_transaction_id, "amount_cents": amount_to_cents(amount)},
        secrets=[cfg["api_key"], cfg["hmac_secret"], token],
    )
    if err or not isinstance(data, dict) or not (_truthy(data.get("success")) or _truthy(data.get("is_refunded"))):
        raise GatewayError(f"Paymob refund was not confirmed: {err or data}")
    return {"reference": str(data.get("id", ""))}
