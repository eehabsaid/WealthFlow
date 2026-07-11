from __future__ import annotations

from decimal import Decimal, InvalidOperation

from core.models import AssetMortgage, AssetRental, AssetSale, BalanceEntry

REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
RENTAL_BALANCE_NOTE_PREFIX = "wealthflow:rental-income:asset:"
MORTGAGE_BALANCE_NOTE_PREFIX = "wealthflow:mortgage-liability:asset:"

def _to_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

class FinancialSyncService:
    def __init__(self):
        from core.services.balance.net_worth_service import NetWorthService

        self._net_worth_service = NetWorthService()

    def _rental_balance_note(self, asset_id: int) -> str:
        return f"{RENTAL_BALANCE_NOTE_PREFIX}{asset_id}"

    def _mortgage_balance_note(self, asset_id: int) -> str:
        return f"{MORTGAGE_BALANCE_NOTE_PREFIX}{asset_id}"

    def rental_income_amount(self, rental: AssetRental | None) -> Decimal:
        if rental is None:
            return Decimal("0")

        monthly_rent = _to_decimal(rental.monthly_rent)
        occupancy_rate = _to_decimal(rental.occupancy_rate)
        return (monthly_rent * occupancy_rate / Decimal("100")).quantize(
            Decimal("0.01")
        )

    def monthly_rental_income_total(self) -> Decimal:
        total = Decimal("0")
        rentals = (
            AssetRental.objects.select_related("asset")
            .filter(asset__asset_type__in=REAL_ESTATE_ASSET_TYPES, asset__status="Owned")
            .order_by("id")
        )
        for rental in rentals:
            total += self.rental_income_amount(rental)
        return total.quantize(Decimal("0.01"))

    def period_rental_income_total(self, period: str | None = None) -> Decimal:
        monthly_total = self.monthly_rental_income_total()
        period_value = str(period or "month").strip().lower()

        if period_value == "year":
            return (monthly_total * Decimal("12")).quantize(Decimal("0.01"))
        return monthly_total

    def sync_rental_balance(self, rental: AssetRental | None):
        if rental is None:
            return

        self.sync_deleted_rental_balance(rental)

    def sync_deleted_rental_balance(self, rental: AssetRental | None):
        if rental is None:
            return

        marker = self._rental_balance_note(rental.asset_id)
        BalanceEntry.objects.filter(notes=marker).delete()

    def sync_mortgage_balance(self, mortgage: AssetMortgage | None):
        if mortgage is None:
            return

        self.sync_deleted_mortgage_balance(mortgage)

    def sync_deleted_mortgage_balance(self, mortgage: AssetMortgage | None):
        if mortgage is None:
            return

        marker = self._mortgage_balance_note(mortgage.asset_id)
        BalanceEntry.objects.filter(notes=marker).delete()

    def sync_asset_sale_balance(self, sale: AssetSale | None, previous_balance_id=None, previous_amount=None):
        if sale is None:
            return

        current_balance_id = sale.deposit_balance_id
        current_amount = _to_decimal(sale.net_sale_amount)
        previous_balance_id = previous_balance_id or getattr(sale, "_previous_deposit_balance_id", None)
        previous_amount = _to_decimal(
            previous_amount if previous_amount is not None else getattr(sale, "_previous_net_sale_amount", 0)
        )

        if previous_balance_id and previous_balance_id != current_balance_id and previous_amount > 0:
            previous_entry = BalanceEntry.objects.filter(pk=previous_balance_id).first()
            if previous_entry is not None:
                previous_entry.amount = _to_decimal(previous_entry.amount) - previous_amount
                previous_entry.save(update_fields=["amount"])

        if current_balance_id:
            current_entry = BalanceEntry.objects.filter(pk=current_balance_id).first()
            if current_entry is not None:
                if previous_balance_id == current_balance_id and previous_amount > 0:
                    current_entry.amount = _to_decimal(current_entry.amount) - previous_amount + current_amount
                else:
                    current_entry.amount = _to_decimal(current_entry.amount) + current_amount
                current_entry.save(update_fields=["amount"])

    def sync_deleted_asset_sale_balance(self, sale: AssetSale | None):
        if sale is None:
            return

        balance_id = sale.deposit_balance_id
        amount = _to_decimal(sale.net_sale_amount)
        if not balance_id or amount <= 0:
            return

        entry = BalanceEntry.objects.filter(pk=balance_id).first()
        if entry is None:
            return

        entry.amount = _to_decimal(entry.amount) - amount
        entry.save(update_fields=["amount"])

    def refresh_portfolio(self):
        return self._net_worth_service.balance_payload()

    def refresh_forecast(self):
        return self._net_worth_service.certificate_forecast_payload()
