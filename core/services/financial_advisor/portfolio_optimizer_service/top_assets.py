"""Top-10 asset breakdown across fixed asset types and certificates.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
Kept in its own file since it's the single largest method on the service.
"""
from __future__ import annotations

from typing import Dict, List

from core.models import BankCertificate, FixedAsset, _is_certificate_active

from .shared import _to_float


class TopAssetsMixin:
    def _top_assets(self, comp: dict, total_portfolio: float) -> List[dict]:
        rows: List[dict] = []
        rates = comp.get("rates", {})

        fixed_assets = list(FixedAsset.objects.filter(status="Owned").order_by("name"))
        by_type: Dict[str, List[FixedAsset]] = {
            "Real Estate": [],
            "Vehicles": [],
            "Gold": [],
            "Other Assets": [],
        }
        for asset in fixed_assets:
            by_type.setdefault(str(asset.asset_type or "Other Assets"), []).append(asset)

        def _asset_group(group_key: str, type_name: str, default_name_key: str):
            items = by_type.get(group_key, [])
            if not items:
                return
            count = len(items)
            serialized_items = [item.to_dict() for item in items]
            total_value = sum(_to_float(data.get("current_market_value")) for data in serialized_items)
            total_investment = sum(_to_float(data.get("total_investment")) for data in serialized_items)
            gain = sum(_to_float(data.get("gain_loss")) for data in serialized_items)
            if count == 1:
                name = items[0].name
            else:
                name = f"{type_name} ({count})"
            rows.append(
                {
                    "asset": name,
                    "asset_name_key": default_name_key if count == 0 else "",
                    "type": type_name,
                    "value": round(total_value, 2),
                    "portfolio_pct": round((total_value / total_portfolio) * 100.0 if total_portfolio > 0 else 0.0, 2),
                    "gain": round(gain, 2),
                    "gain_pct": round((gain / total_investment) * 100.0, 2) if total_investment > 0 else 0.0,
                    "count": count,
                }
            )

        _asset_group("Real Estate", "Real Estate", "portfolio_optimizer_asset_real_estate")
        _asset_group("Vehicles", "Vehicles", "portfolio_optimizer_asset_vehicles")
        _asset_group("Gold", "Gold Holdings", "portfolio_optimizer_asset_gold")
        _asset_group("Other Assets", "Other Assets", "portfolio_optimizer_asset_other_assets")

        active_certs = [c for c in BankCertificate.objects.select_related("currency").all() if _is_certificate_active(c)]
        cert_count = len(active_certs)
        if cert_count > 0:
            cert_value = 0.0
            cert_gain = 0.0
            for cert in active_certs:
                code = str(cert.currency.code if cert.currency else "EGP").upper()
                amount = _to_float(cert.amount)
                converted = amount if code == "EGP" else amount * _to_float(rates.get(code))
                cert_value += converted
                cert_gain += _to_float(cert.interest_value)
            rows.append(
                {
                    "asset": f"Certificates ({cert_count})",
                    "asset_name_key": "",
                    "type": "Certificates",
                    "value": round(cert_value, 2),
                    "portfolio_pct": round((cert_value / total_portfolio) * 100.0 if total_portfolio > 0 else 0.0, 2),
                    "gain": round(cert_gain, 2),
                    "gain_pct": 0.0,
                    "count": cert_count,
                }
            )

        rows.sort(key=lambda item: item["value"], reverse=True)
        return rows[:10]
