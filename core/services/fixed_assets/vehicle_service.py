# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from core.models import (
    VehicleDetails,

)
from core.constants import (
    VEHICLE_ASSET_TYPES,
)
from core.utils import (
    _parse_iso_date,
)


def _sync_vehicle_details(asset, details_data):
    if asset.asset_type not in VEHICLE_ASSET_TYPES or not details_data:
        if hasattr(asset, "vehicle_details"):
            asset.vehicle_details.delete()
        return

    VehicleDetails.objects.update_or_create(
        asset=asset,
        defaults={
            "brand": details_data.get("brand", ""),
            "model": details_data.get("model", ""),
            "year": details_data.get("year") or None,
            "vin": details_data.get("vin", ""),
            "engine": details_data.get("engine", ""),
            "transmission": details_data.get("transmission", ""),
            "fuel_type": details_data.get("fuel_type", ""),
            "mileage": details_data.get("mileage", 0),
            "plate_number": details_data.get("plate_number", ""),
            "license_expiry_date": _parse_iso_date(details_data.get("license_expiry_date")),
            "color": details_data.get("color", ""),
        },
    )


