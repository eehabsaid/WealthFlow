from core.views.auth_views import AdminRequiredMixin
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AppSettings,
    ExchangeRate,
    GoldPrice,
    Currency,
    GoldTypeSetting,
    GoldPuritySetting,
    EmailTemplate,

)

from core.services.shared.exchange_rate_service import ExchangeRateService
from core.services.fixed_assets.gold_valuation_service import GoldValuationService
from core.services.shared.auth_workflow_service import AuthWorkflowService, EmailTemplateService

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class CurrencyListView(View):
    def get(self, request):
        currencies = Currency.objects.all().order_by("order")
        return JsonResponse({"currencies": [c.to_dict() for c in currencies]})

    def post(self, request):
        data = json.loads(request.body)
        currency = Currency.objects.create(
            code=data["code"],
            symbol=data.get("symbol", ""),
            flag=data.get("flag", "💱"),
            name=data.get("name", data["code"]),
            order=data.get("order", 0),
        )
        return JsonResponse(currency.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class CurrencyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        data = json.loads(request.body)
        for field in ["code", "symbol", "flag", "name", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class SettingsView(View):
    def get(self, request):
        settings = AppSettings.objects.all()
        return JsonResponse({"settings": {s.key: s.value for s in settings}})

    def post(self, request):
        data = json.loads(request.body)
        obj = AppSettings.set(data["key"], data["value"])
        return JsonResponse({"key": obj.key, "value": obj.value})

@method_decorator(csrf_exempt, name="dispatch")
class EmailTemplateListView(AdminRequiredMixin, View):
    def get(self, request):
        lang = request.GET.get("lang", "en")
        return JsonResponse({"items": EmailTemplateService.list_templates(lang)})

@method_decorator(csrf_exempt, name="dispatch")
class EmailTemplateDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        lang = request.GET.get("lang", "en")
        template = get_object_or_404(EmailTemplate, pk=pk)
        EmailTemplateService.ensure_defaults()
        return JsonResponse(template.to_dict(lang))

    def put(self, request, pk):
        template = get_object_or_404(EmailTemplate, pk=pk)
        data = json.loads(request.body)
        lang = str(data.get("lang", "en") or "en")
        updated = EmailTemplateService.update_template(
            template,
            lang=lang,
            subject=(data.get("subject") or "").strip(),
            body=(data.get("body") or "").strip(),
        )
        return JsonResponse(updated.to_dict(lang))

@method_decorator(csrf_exempt, name="dispatch")
class EmailSettingsTestView(AdminRequiredMixin, View):
    def post(self, request):
        data = json.loads(request.body or "{}")
        recipient = (data.get("to_email") or "").strip()
        if not recipient:
            recipient = (
                AppSettings.get("administrator_notification_email", "").strip()
                or AppSettings.get("sender_email", "").strip()
            )

        ok, message_key = AuthWorkflowService.send_smtp_test_email(to_email=recipient)
        return JsonResponse(
            {
                "ok": ok,
                "message_key": message_key,
            },
            status=200 if ok else 400,
        )

def _seed_gold_settings_defaults():
    default_types = [
        ("Coins", 1),
        ("Bars", 2),
        ("Jewelry", 3),
    ]
    for name, order in default_types:
        GoldTypeSetting.objects.get_or_create(
            name=name,
            defaults={"is_active": True, "order": order},
        )

    default_purities = [
        ("24k", "24K", 0),
        ("22k", "22K", 0),
        ("21k", "21K", 0),
        ("18k", "18K", 0),
    ]
    for key, label, order in default_purities:
        GoldPuritySetting.objects.get_or_create(
            key=key,
            defaults={
                "label": label,
                "cashback_per_gram": 0,
                "is_active": True,
                "order": order,
            },
        )

@method_decorator(csrf_exempt, name="dispatch")
class GoldTypeSettingsListView(View):
    def get(self, request):
        _seed_gold_settings_defaults()
        rows = GoldTypeSetting.objects.all()
        return JsonResponse({"items": [row.to_dict() for row in rows]})

    def post(self, request):
        data = json.loads(request.body)
        item = GoldTypeSetting.objects.create(
            name=(data.get("name") or "").strip(),
            is_active=bool(data.get("is_active", True)),
            order=int(data.get("order", 0) or 0),
        )
        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class GoldTypeSettingsDetailView(View):
    def put(self, request, pk):
        item = get_object_or_404(GoldTypeSetting, pk=pk)
        data = json.loads(request.body)
        for field in ["name", "is_active", "order"]:
            if field in data:
                setattr(item, field, data[field])
        item.save()
        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(GoldTypeSetting, pk=pk)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"disabled": pk})

@method_decorator(csrf_exempt, name="dispatch")
class GoldPuritySettingsListView(View):
    def get(self, request):
        _seed_gold_settings_defaults()
        rows = GoldPuritySetting.objects.all()
        return JsonResponse({"items": [row.to_dict() for row in rows]})

    def post(self, request):
        data = json.loads(request.body)
        key = str(data.get("key") or "").strip().lower()
        if key and not key.endswith("k"):
            key = f"{key}k"
        item = GoldPuritySetting.objects.create(
            key=key,
            label=(data.get("label") or "").strip() or key.upper(),
            cashback_per_gram=Decimal(str(data.get("cashback_per_gram", 0) or 0)),
            is_active=bool(data.get("is_active", True)),
            order=int(data.get("order", 0) or 0),
        )
        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class GoldPuritySettingsDetailView(View):
    def put(self, request, pk):
        item = get_object_or_404(GoldPuritySetting, pk=pk)
        data = json.loads(request.body)

        if "key" in data:
            key = str(data.get("key") or "").strip().lower()
            if key and not key.endswith("k"):
                key = f"{key}k"
            item.key = key

        if "label" in data:
            item.label = (data.get("label") or "").strip()

        if "cashback_per_gram" in data:
            item.cashback_per_gram = Decimal(str(data.get("cashback_per_gram") or 0))

        if "is_active" in data:
            item.is_active = bool(data.get("is_active"))

        if "order" in data:
            item.order = int(data.get("order") or 0)

        item.save()
        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(GoldPuritySetting, pk=pk)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"disabled": pk})

# ── Exchange Rates views ──────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateListView(View):
    """GET  /api/rates/          → latest rate per currency
    POST /api/rates/refresh/  → fetch from internet and save"""

    def get(self, request):
        """Return the single most-recent row per currency code."""
        from django.db.models import Max

        latest_ids = (
            ExchangeRate.objects.values("currency_code")
            .annotate(max_id=Max("id"))
            .values_list("max_id", flat=True)
        )
        rates = ExchangeRate.objects.filter(id__in=latest_ids).order_by("currency_code")
        last = ExchangeRate.objects.order_by("-fetched_at").first()
        return JsonResponse(
            {
                "rates": [r.to_dict() for r in rates],
                "fetched_at": (
                    last.fetched_at.strftime("%Y-%m-%d %H:%M") if last else None
                ),
            }
        )

@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateRefreshView(View):
    """Calls open.er-api.com and saves latest rates to DB."""

    def post(self, request):
        try:
            result = ExchangeRateService().refresh_latest_rates().to_dict()
            return JsonResponse({**result, "message": f"Fetched {result['saved']} currencies"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)

# ── Gold Price views ──────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceListView(View):
    """GET /api/gold/ → latest gold price"""

    def get(self, request):
        latest = GoldPrice.objects.order_by("-fetched_at").first()
        if not latest:
            return JsonResponse(
                {"gold": None, "message": "No data yet. Click Refresh."}
            )
        return JsonResponse({"gold": latest.to_dict()})

@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceRefreshView(View):
    """Fetches EGP gold prices from goldbullioneg.com and USD/EGP from open.er-api.com."""

    def get(self, request):
        return self.post(request)

    def post(self, request):
        try:
            result = GoldValuationService().refresh_latest_prices().to_dict()
            latest = GoldPrice.objects.order_by("-fetched_at").first()
            return JsonResponse({**result, "gold": latest.to_dict() if latest else None})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)

# ══════════════════════════════════════════════════════════════
# EXPENSE VIEWS
# ══════════════════════════════════════════════════════════════

