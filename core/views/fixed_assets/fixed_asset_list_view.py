# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from core.models import (
    FixedAsset,
    RealEstateDetails,
)
from core.services.balance.net_worth_service import NetWorthService
from core.services.fixed_assets.asset_purchase_service import _apply_asset_purchase_rows_delta, _normalize_purchase_payments_payload, _sync_asset_purchase_payments
from core.services.fixed_assets.vehicle_service import _sync_vehicle_details
from core.services.fixed_assets.gold_sync_service import _sync_gold_balance_from_assets, _sync_gold_details
from core.services.fixed_assets.property_service import _sync_asset_mortgage, _sync_asset_rental, _sync_other_asset_details
from core.services.fixed_assets.asset_maintenance_service import _sync_asset_furniture, _sync_asset_insurance, _sync_asset_maintenance, _sync_asset_valuation_history
from core.services.fixed_assets.asset_cost_sync_service import _sync_asset_renovations, _sync_asset_acquisition_costs
from core.views.fixed_assets.fixed_asset_helpers import (
    _resolve_asset_usd_rate_and_price,
    _clear_non_selected_asset_details,
)


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetListView(View):

    def get(self, request):
        qs = (
            FixedAsset.objects.select_related(
                "real_estate",
                "vehicle_details",
                "gold_details",
                "other_asset_details",
                "sale",
                "mortgage",
                "rental",
            )
            .prefetch_related(
                "acquisition_costs",
                "renovations",
                "maintenance",
                "insurance",
                "furniture",
                "valuation_history",
                "purchase_payments",
                "purchase_payments__currency",
            )
            .all()
            .order_by("name")
        )

        asset_type = request.GET.get("asset_type")
        status = request.GET.get("status")

        if asset_type:
            qs = qs.filter(asset_type=asset_type)

        if status:
            qs = qs.filter(status=status)

        service = NetWorthService()
        return JsonResponse(
            {
                "assets": [a.to_dict() for a in qs],
                "portfolio_snapshot": service.fixed_assets_snapshot(),
            }
        )

    def post(self, request):
        data = json.loads(request.body)
        re = data.get("real_estate_details")
        vehicle_details = data.get("vehicle_details")
        gold_details = data.get("gold_details")
        other_asset_details = data.get("other_asset_details")

        purchase_rows_raw = data.get("purchase_payments", [])

        try:
            with transaction.atomic():
                purchase_rows = _normalize_purchase_payments_payload(
                    purchase_rows_raw,
                    data.get("purchase_price", 0),
                    purchase_currency_id=data.get("purchase_currency_id"),
                )

                usd_rate, price_usd = _resolve_asset_usd_rate_and_price(data)

                asset = FixedAsset.objects.create(
                    name=data["name"],
                    asset_type=data["asset_type"],
                    status=data.get("status", "Owned"),
                    purchase_date=data["purchase_date"],
                    purchase_price=data.get("purchase_price", 0),
                    purchase_usd_rate=usd_rate,
                    purchase_price_usd=price_usd,
                    current_market_value=data.get("current_market_value", 0),
                    valuation_source=data.get("valuation_source", "Manual"),
                    last_valuation_date=data.get("last_valuation_date") or None,
                    notes=data.get("notes", ""),
                )

                if re:
                    RealEstateDetails.objects.create(
                        asset=asset,
                        country=re.get("country", "Egypt"),
                        governorate=re.get("governorate", ""),
                        city=re.get("city", ""),
                        district=re.get("district", ""),
                        full_address=re.get("address", ""),
                        area_m2=re.get("apartment_area", 0),
                        bedrooms=re.get("rooms", 0),
                        bathrooms=re.get("bathrooms", 0),
                        floor_number=re.get("floor", 0),
                        building_floors=re.get("building_floors", 0),
                        build_year=re.get("building_year") or None,
                        facing=re.get("facades", ""),
                        finishing_level=re.get("finishing_level", ""),
                        electricity_meter_private=re.get("electricity", False),
                        water_meter_private=re.get("water", False),
                        has_gas=re.get("gas", False),
                        has_elevator=re.get("elevator", False),
                        has_garage=re.get("garage", False),
                        has_land_share=re.get("has_land_share", False),
                        land_share_ratio=re.get("land_share", ""),
                        land_share_sqm=float(re.get("land_share_sqm") or 0),
                        latitude=re.get("latitude") or None,
                        longitude=re.get("longitude") or None,
                        licensed=re.get("licensed", False),
                        description=re.get("description", ""),
                    )

                _sync_vehicle_details(asset, vehicle_details)
                _sync_gold_details(asset, gold_details)
                _sync_other_asset_details(asset, other_asset_details)

                _sync_asset_mortgage(asset, data.get("mortgage_details"))
                _sync_asset_rental(asset, data.get("rental_details"))

                _sync_asset_renovations(asset, data.get("renovations", []))
                _sync_asset_acquisition_costs(asset, data.get("acquisition_costs", []))

                _sync_asset_maintenance(asset, data.get("maintenance", []))
                _sync_asset_insurance(asset, data.get("insurance", []))
                _sync_asset_furniture(asset, data.get("furniture", []))
                _sync_asset_valuation_history(asset, data.get("valuation_history", []))
                _clear_non_selected_asset_details(asset)

                _apply_asset_purchase_rows_delta(purchase_rows, sign=-1)
                _sync_asset_purchase_payments(asset, purchase_rows)

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(asset.to_dict(), status=201)
