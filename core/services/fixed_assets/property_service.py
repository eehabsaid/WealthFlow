# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal
from django.db import transaction
from core.models import (
    OtherAssetDetails,
    AssetMortgage,
    AssetRental,

)
from core.constants import (
    REAL_ESTATE_ASSET_TYPES,
    OTHER_ASSET_TYPES,
)
from core.utils import (
    _parse_iso_date,
)
from core.services.expenses.expense_service import _apply_expense_balance_delta

def _sync_other_asset_details(asset, details_data):
    if asset.asset_type not in OTHER_ASSET_TYPES or not details_data:
        if hasattr(asset, "other_asset_details"):
            asset.other_asset_details.delete()
        return

    OtherAssetDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "category": details_data.get("category", ""),
            "manufacturer": details_data.get("manufacturer", ""),
            "model": details_data.get("model", ""),
            "serial_number": details_data.get("serial_number", ""),
            "description": details_data.get("description", ""),
            "warranty_expiry": details_data.get("warranty_expiry") or None,
            "notes": details_data.get("notes", ""),
        },
    )

def _sync_asset_mortgage(asset, mortgage_data):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES or not mortgage_data:
        if hasattr(asset, "mortgage"):
            asset.mortgage.delete()
        return

    has_values = any(
        mortgage_data.get(key) not in (None, "", 0, 0.0)
        for key in [
            "loan_amount",
            "remaining_balance",
            "monthly_installment",
            "interest_rate",
            "start_date",
            "end_date",
        ]
    )

    if not has_values:
        if hasattr(asset, "mortgage"):
            asset.mortgage.delete()
        return

    AssetMortgage.objects.update_or_create(
        asset=asset,
        defaults={
            "loan_amount": mortgage_data.get("loan_amount", 0),
            "remaining_balance": mortgage_data.get("remaining_balance", 0),
            "monthly_installment": mortgage_data.get("monthly_installment", 0),
            "interest_rate": mortgage_data.get("interest_rate", 0),
            "start_date": _parse_iso_date(mortgage_data.get("start_date")),
            "end_date": _parse_iso_date(mortgage_data.get("end_date")),
        },
    )

def _sync_asset_rental(asset, rental_data):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES or not rental_data:
        if hasattr(asset, "rental"):
            _reverse_rental_balance(asset.rental)
            asset.rental.delete()
        return

    has_values = any(
        rental_data.get(key) not in (None, "", 0, 0.0)
        for key in [
            "monthly_rent",
            "occupancy_rate",
            "tenant_name",
            "contract_start",
            "contract_end",
            "notes",
        ]
    )

    if not has_values:
        if hasattr(asset, "rental"):
            _reverse_rental_balance(asset.rental)
            asset.rental.delete()
        return

    previous_rental = getattr(asset, "rental", None)
    previous_method = previous_rental.receive_method if previous_rental else None
    previous_bank_id = previous_rental.bank_id if previous_rental else None
    previous_amount = Decimal(str(previous_rental.monthly_rent or 0)) if previous_rental else Decimal("0")

    with transaction.atomic():
        rental, _ = AssetRental.objects.update_or_create(
            asset=asset,
            defaults={
                "monthly_rent": rental_data.get("monthly_rent", 0),
                "occupancy_rate": rental_data.get("occupancy_rate", 0),
                "tenant_name": rental_data.get("tenant_name", ""),
                "contract_start": _parse_iso_date(rental_data.get("contract_start")),
                "contract_end": _parse_iso_date(rental_data.get("contract_end")),
                "receive_method": rental_data.get("receive_method", "Cash"),
                "bank_id": rental_data.get("bank_id"),
                "notes": rental_data.get("notes", ""),
            },
        )

        if previous_amount > 0 and previous_method:
            _apply_expense_balance_delta(previous_method, previous_bank_id, -previous_amount)

        new_amount = Decimal(str(rental.monthly_rent or 0))
        if new_amount > 0:
            _apply_expense_balance_delta(rental.receive_method, rental.bank_id, new_amount)

def _reverse_rental_balance(rental):
    if rental is None:
        return
    amount = Decimal(str(rental.monthly_rent or 0))
    if amount > 0 and rental.receive_method:
        _apply_expense_balance_delta(rental.receive_method, rental.bank_id, -amount)

