# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from core.models import RealEstateDetails
from core.constants import (
    REAL_ESTATE_ASSET_TYPES,
    VEHICLE_ASSET_TYPES,
    GOLD_ASSET_TYPES,
    OTHER_ASSET_TYPES,
)


def _clear_non_selected_asset_details(asset):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES and hasattr(asset, "real_estate"):
        asset.real_estate.delete()

    if asset.asset_type not in VEHICLE_ASSET_TYPES and hasattr(asset, "vehicle_details"):
        asset.vehicle_details.delete()

    if asset.asset_type not in GOLD_ASSET_TYPES and hasattr(asset, "gold_details"):
        asset.gold_details.delete()

    if asset.asset_type not in OTHER_ASSET_TYPES and hasattr(asset, "other_asset_details"):
        asset.other_asset_details.delete()

def _resolve_asset_usd_rate_and_price(data, current_usd_rate=0, current_price_usd=0):
    from decimal import Decimal
    from core.models import Currency
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    purchase_price = Decimal(str(data.get("purchase_price", 0) or 0))
    usd_rate = Decimal(str(data.get("purchase_usd_rate", current_usd_rate) or 0))
    price_usd = Decimal(str(data.get("purchase_price_usd", current_price_usd) or 0))
    purchase_currency_id = data.get("purchase_currency_id")

    code = "EGP"
    if purchase_currency_id:
        c = Currency.objects.filter(id=purchase_currency_id).first()
        if c:
            code = c.code.upper()

    if usd_rate <= 0:
        if code == "USD":
            usd_rate = Decimal("1.000000")
        else:
            usd_rate = CurrencyConversionService.calculate_exchange_rate(code, "USD")

    if price_usd <= 0 and purchase_price > 0 and usd_rate > 0:
        if code == "USD":
            price_usd = purchase_price
        elif code == "EGP":
            price_usd = (purchase_price * usd_rate).quantize(Decimal("0.01"))
        else:
            price_usd = (purchase_price * usd_rate).quantize(Decimal("0.01"))

    return usd_rate, price_usd

def _sync_real_estate_details_for_update(asset, re):
    """Update-or-clear RealEstateDetails for an existing asset from a PUT payload.

    Mirrors the previous inline block in FixedAssetDetailView.put() exactly —
    same field mapping, same get_or_create/delete behavior, no logic changes.
    """
    if re:
        obj, _ = RealEstateDetails.objects.get_or_create(asset=asset)

        obj.country = re.get("country", "Egypt")
        obj.governorate = re.get("governorate", "")
        obj.city = re.get("city", "")
        obj.district = re.get("district", "")
        obj.full_address = re.get("address", "")

        obj.area_m2 = re.get("apartment_area", 0)

        obj.bedrooms = re.get("rooms", 0)
        obj.bathrooms = re.get("bathrooms", 0)

        obj.floor_number = re.get("floor", 0)
        obj.building_floors = re.get("building_floors", 0)
        obj.build_year = re.get("building_year") or None

        obj.facing = re.get("facades", "")

        obj.furnished_status = re.get("furnished_status", "Unfurnished")
        obj.finishing_level = re.get("finishing_level", "")

        obj.electricity_meter_private = re.get("electricity", False)
        obj.water_meter_private = re.get("water", False)
        obj.has_gas = re.get("gas", False)

        obj.has_elevator = re.get("elevator", False)
        obj.has_garage = re.get("garage", False)
        obj.has_land_share = re.get("has_land_share", False)
        obj.land_share_ratio = re.get("land_share", "")
        obj.land_share_sqm = float(re.get("land_share_sqm") or 0)
        obj.latitude = re.get("latitude") or None
        obj.longitude = re.get("longitude") or None
        obj.licensed = re.get("licensed", False)
        obj.description = re.get("description", "")

        obj.save()
    elif asset.asset_type not in REAL_ESTATE_ASSET_TYPES and hasattr(asset, "real_estate"):
        asset.real_estate.delete()
