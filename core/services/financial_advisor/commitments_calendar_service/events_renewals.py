"""
Commitments calendar event derivation (renewals, recurring, asset sales).

Pure derivation: reads existing records, never posts anything, never
touches balances. Split from events.py to stay within the 200-line file
limit. See events.py for the shared event shape and kind semantics.
"""
from __future__ import annotations

from typing import List

from core.models import AssetInsurance, AssetRental, AssetSale, RecurringTransaction, VehicleDetails
from core.services.budgets.recurring_service import _advance

from .event_shape import _in_range, _make, _to_float


class RenewalEventsMixin:
    # Recurring transactions (bills, subscriptions, rent...) — expected outflows.
    def _recurring_events(self) -> List[dict]:
        out: List[dict] = []
        recs = RecurringTransaction.objects.select_related("currency", "bank").filter(
            owner=self.owner, is_active=True
        )
        for rec in recs:
            run = rec.next_run_date
            safety = 0
            while run <= self.end and safety < 366:
                safety += 1
                if rec.end_date and run > rec.end_date:
                    break
                if _in_range(self.start, self.end, run):
                    out.append(
                        _make(
                            run,
                            "expense",
                            "recurring",
                            "expected",
                            "commitments_event_recurring",
                            amount=_to_float(rec.amount),
                            currency_code=rec.currency.code if rec.currency else "",
                            source="RecurringTransaction",
                            source_id=rec.id,
                            bank_id=rec.bank_id,
                            status="active",
                            extra={"name": rec.name},
                        )
                    )
                run = _advance(run, rec.frequency, rec.interval)
        return out

    # Asset sales — actual future income the forecast already models.
    def _asset_sale_events(self) -> List[dict]:
        out: List[dict] = []
        sales = (
            AssetSale.objects.select_related("asset")
            .filter(
                asset__owner=self.owner,
                sale_date__gte=self.start,
                sale_date__lte=self.end,
                net_sale_amount__gt=0,
            )
            .order_by("sale_date", "id")
        )
        for sale in sales:
            out.append(
                _make(
                    sale.sale_date,
                    "income",
                    "asset_sale",
                    "actual",
                    "commitments_event_asset_sale",
                    amount=_to_float(sale.net_sale_amount),
                    amount_base=_to_float(sale.net_sale_amount),
                    source="AssetSale",
                    source_id=sale.id,
                    status="scheduled",
                )
            )
        return out

    # Insurance renewals — informational, no automatic expense.
    def _insurance_events(self) -> List[dict]:
        out: List[dict] = []
        rows = (
            AssetInsurance.objects.select_related("asset")
            .filter(
                asset__owner=self.owner,
                expiry_date__gte=self.start,
                expiry_date__lte=self.end,
            )
            .order_by("expiry_date", "id")
        )
        for ins in rows:
            out.append(
                _make(
                    ins.expiry_date,
                    "renewal",
                    "insurance_renewal",
                    "informational",
                    "commitments_event_insurance_renewal",
                    amount=_to_float(ins.premium),
                    source="AssetInsurance",
                    source_id=ins.id,
                    status="renewal_due",
                    extra={"company": ins.company},
                )
            )
        return out

    # Vehicle license renewals — informational, no automatic expense.
    def _vehicle_license_events(self) -> List[dict]:
        out: List[dict] = []
        rows = (
            VehicleDetails.objects.select_related("asset")
            .filter(
                asset__owner=self.owner,
                license_expiry_date__gte=self.start,
                license_expiry_date__lte=self.end,
            )
            .order_by("license_expiry_date", "id")
        )
        for v in rows:
            out.append(
                _make(
                    v.license_expiry_date,
                    "renewal",
                    "vehicle_license_renewal",
                    "informational",
                    "commitments_event_vehicle_license",
                    source="VehicleDetails",
                    source_id=v.id,
                    status="renewal_due",
                    extra={"plate": v.plate_number},
                )
            )
        return out

    # Rental contract expiry — informational, no automatic expense.
    def _rental_contract_events(self) -> List[dict]:
        out: List[dict] = []
        rows = (
            AssetRental.objects.select_related("asset", "bank")
            .filter(
                asset__owner=self.owner,
                contract_end__gte=self.start,
                contract_end__lte=self.end,
            )
            .order_by("contract_end", "id")
        )
        for r in rows:
            out.append(
                _make(
                    r.contract_end,
                    "renewal",
                    "rental_contract_expiry",
                    "informational",
                    "commitments_event_rental_contract",
                    source="AssetRental",
                    source_id=r.asset_id,
                    bank_id=r.bank_id,
                    status="renewal_due",
                    extra={"tenant": r.tenant_name},
                )
            )
        return out
