"""'Rent received': books the real deposit for one month of a rental and settles that month's virtual rental income."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core.models import AssetRental, Currency, RentReceipt
from core.services.balance.financial_sync_service import FinancialSyncService
from core.services.shared.base_currency import get_user_base_code


class RentReceiptError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def month_start(value) -> date:
    """'YYYY-MM', 'YYYY-MM-DD' or a date -> first day of that month."""
    if isinstance(value, date):
        return value.replace(day=1)
    try:
        parts = str(value).strip().split("-")
        return date(int(parts[0]), int(parts[1]), 1)
    except (ValueError, IndexError) as exc:
        raise RentReceiptError("Invalid month. Use YYYY-MM.") from exc


def settled_rental_ids(owner, on_date: date | None = None) -> set:
    """Rentals whose rent for the month of `on_date` (default: today) was already received."""
    period = month_start(on_date or timezone.localdate())
    return set(RentReceipt.objects.filter(owner=owner, period_start=period).values_list("rental_id", flat=True))


def record_receipt(owner, rental: AssetRental, *, period=None, amount=None, received_date=None, notes: str = "") -> RentReceipt:
    if rental.asset.owner_id != owner.id:
        raise RentReceiptError("Rental not found.", 404)
    period_start = month_start(period or timezone.localdate())
    if amount in (None, ""):
        value = FinancialSyncService().rental_income_amount(rental)
    else:
        try:
            value = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise RentReceiptError("Invalid amount.") from exc
    if value <= 0:
        raise RentReceiptError("Amount must be greater than zero. Set the monthly rent and occupancy, or enter the amount received.")
    if RentReceipt.objects.filter(rental=rental, period_start=period_start).exists():
        raise RentReceiptError("Rent for this month was already recorded as received.", 409)
    currency = Currency.objects.filter(owner=owner, code__iexact=get_user_base_code(owner)).first()
    if currency is None:
        raise RentReceiptError("Your default currency is missing; add it first.")
    use_bank = rental.bank if rental.receive_method != "Cash" else None
    with transaction.atomic():
        receipt = RentReceipt.objects.create(
            owner=owner, rental=rental, period_start=period_start, received_date=received_date or timezone.localdate(),
            bank=use_bank, currency=currency, amount=value, notes=notes or "",
        )
        receipt.apply_receipt()
    return receipt


def delete_receipt(receipt: RentReceipt) -> None:
    """Undo: takes the deposit back out of the balance; the month's virtual rent counts again."""
    with transaction.atomic():
        receipt.reverse_receipt()
        receipt.delete()
