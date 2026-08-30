"""
_projected_balance_entries mixin, split out of data_access.py to stay under
the 200-line limit.

NOTE (200-line file convention): this method is self-contained (only reads
BalanceEntry/AssetRental/AssetMortgage/Currency and self._certificate_projection_map,
self._cached), so it was lifted out verbatim rather than being merged into
data_access.py.
"""
from __future__ import annotations

from typing import List

from core.models import AssetMortgage, AssetRental, BalanceEntry, Currency

from .helpers import REAL_ESTATE_ASSET_TYPES, _to_float


class ProjectedBalanceEntriesMixin:
    def _projected_balance_entries(self) -> List[dict]:
        def _load():
            entries = list(BalanceEntry.objects.select_related("bank", "currency").all())
            cert_map = self._certificate_projection_map()
            egp_currency = Currency.objects.filter(code__iexact="EGP").first()
            virtual_entries: List[dict] = []

            def _virtual_entry(title: str, amount: float, source_key: str) -> dict:
                currency = egp_currency
                return {
                    "id": f"virtual-{source_key}",
                    "title": title,
                    "balance_type": BalanceEntry.BalanceType.CASH,
                    "bank_id": None,
                    "bank_name": "",
                    "currency_id": currency.id if currency else None,
                    "currency_code": currency.code if currency else "EGP",
                    "currency_symbol": currency.symbol if currency else "",
                    "currency_flag": currency.flag if currency else "💱",
                    "currency_name": currency.name if currency else "Egyptian Pound",
                    "purity": "",
                    "amount": round(amount, 2),
                    "notes": "",
                }

            rental_qs = (
                AssetRental.objects.select_related("asset")
                .filter(asset__asset_type__in=REAL_ESTATE_ASSET_TYPES, asset__status="Owned")
                .order_by("id")
            )
            for rental in rental_qs:
                monthly_rent = _to_float(rental.monthly_rent)
                occupancy_rate = _to_float(rental.occupancy_rate)
                rental_income = monthly_rent * occupancy_rate / 100.0
                if rental_income <= 0:
                    continue
                virtual_entries.append(
                    _virtual_entry(
                        f"{rental.asset.name} Rental Income",
                        rental_income,
                        f"rental-income-{rental.id}",
                    )
                )

            mortgage_qs = (
                AssetMortgage.objects.select_related("asset")
                .filter(asset__asset_type__in=REAL_ESTATE_ASSET_TYPES, asset__status="Owned")
                .order_by("id")
            )
            for mortgage in mortgage_qs:
                remaining_balance = _to_float(mortgage.remaining_balance)
                if remaining_balance <= 0:
                    continue
                virtual_entries.append(
                    _virtual_entry(
                        f"{mortgage.asset.name} Mortgage Liability",
                        -remaining_balance,
                        f"mortgage-liability-{mortgage.id}",
                    )
                )

            payload = []
            for entry in entries:
                if entry.balance_type == BalanceEntry.BalanceType.CERTIFICATE:
                    key = (entry.bank_id or 0, entry.currency_id or 0)
                    active_total = cert_map.get(key, 0.0)
                    if active_total <= 0:
                        continue
                    item = entry.to_dict()
                    item["amount"] = active_total
                    payload.append(item)
                else:
                    payload.append(entry.to_dict())
            payload.extend(virtual_entries)
            return payload

        return self._cached("projected_entries", _load)
