# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""


from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.views.auth_views import AdminRequiredMixin
from core.models import AppSettings


@method_decorator(csrf_exempt, name="dispatch")
class ScrapePropertyRatesView(AdminRequiredMixin, View):
    """
    POST /api/settings/scrape-property-rates/

    Runs the Aqarmap scraper (or baseline-only mode) and saves the result
    into AppSettings['property_valuation_rate_map'].

    Body (optional JSON):
        { "baseline_only": true, "timeout": 25 }
    """

    def post(self, request):
        import json as _json
        from core.services.fixed_assets.aqarmap_scraper import (
            build_rate_map,
            CAIRO_BASELINE,
            GOVERNORATE_BASELINE,
            DEFAULT_RATE,
        )

        try:
            body = _json.loads(request.body or b"{}") if request.body else {}
        except (_json.JSONDecodeError, ValueError):
            body = {}

        baseline_only = bool(body.get("baseline_only", False))
        timeout_secs = int(body.get("timeout", 25))
        timeout_ms = timeout_secs * 1_000

        try:
            if baseline_only:
                rate_map = {
                    "by_city": CAIRO_BASELINE.copy(),
                    "by_governorate": GOVERNORATE_BASELINE.copy(),
                    "default": DEFAULT_RATE,
                    "source": "baseline_only",
                }
            else:
                rate_map = build_rate_map(timeout_ms=timeout_ms)
        except Exception as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=500)

        new_json = _json.dumps(rate_map, ensure_ascii=False, indent=2)
        AppSettings.set("property_valuation_rate_map", new_json)

        # Ensure description is set
        try:
            obj = AppSettings.objects.get(key="property_valuation_rate_map")
            if not obj.description:
                obj.description = (
                    "Auto-updated EGP/sqm rates by district/governorate. "
                    "JSON with keys: by_city, by_governorate, default."
                )
                obj.save(update_fields=["description"])
        except AppSettings.DoesNotExist:
            pass

        return JsonResponse({
            "ok": True,
            "source": rate_map.get("source", "unknown"),
            "districts": len(rate_map.get("by_city", {})),
            "governorates": len(rate_map.get("by_governorate", {})),
            "rate_map_json": new_json,
        })
