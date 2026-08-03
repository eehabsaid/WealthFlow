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
from core.integrations.ai_provider import (
    AVAILABLE_AI_PROVIDERS,
    get_ai_provider,
)

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
# BACKUP & RESTORE VIEWS
# ══════════════════════════════════════════════════════════════
import tempfile
import os
from datetime import datetime
from django.http import FileResponse
from django.conf import settings
from django.core.management import call_command

@method_decorator(csrf_exempt, name="dispatch")
class BackupCreateView(AdminRequiredMixin, View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        download = request.GET.get("download", "false").lower() == "true"
        if download:
            # Create backup in temporary directory
            temp_dir = tempfile.mkdtemp()
            filename = f"wealthflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wfbackup"
            filepath = os.path.join(temp_dir, filename)
            try:
                call_command("backup_data", output=temp_dir, filename=filename)
                # Return file for download
                response = FileResponse(open(filepath, "rb"), content_type="application/zip")
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            # Create backup in default backups directory on the server
            backups_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backups_dir, exist_ok=True)
            filename = f"wealthflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wfbackup"
            try:
                call_command("backup_data", output=backups_dir, filename=filename)
                return JsonResponse({"success": True, "filename": filename})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class BackupListView(AdminRequiredMixin, View):
    def get(self, request):
        backups_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        files = []
        for filename in os.listdir(backups_dir):
            if filename.endswith(".wfbackup"):
                filepath = os.path.join(backups_dir, filename)
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        # Sort files: latest first
        files.sort(key=lambda x: x["created_at"], reverse=True)
        return JsonResponse({"backups": files})

@method_decorator(csrf_exempt, name="dispatch")
class BackupDeleteView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            filename = data.get("filename")
            if not filename or ".." in filename or "/" in filename or "\\" in filename:
                return JsonResponse({"error": "Invalid filename"}, status=400)
            
            backups_dir = os.path.join(settings.BASE_DIR, "backups")
            filepath = os.path.join(backups_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"error": "File not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class BackupRestoreView(AdminRequiredMixin, View):
    def post(self, request):
        overwrite = request.GET.get("overwrite", "false").lower() == "true"
        
        # Check if it's an uploaded file
        if "file" in request.FILES:
            uploaded_file = request.FILES["file"]
            # Save it temporarily
            temp_dir = tempfile.mkdtemp()
            filepath = os.path.join(temp_dir, uploaded_file.name)
            with open(filepath, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            
            try:
                # Run restore command
                call_command("restore_data", filepath, overwrite=overwrite)
                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
            finally:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        else:
            # Server-side file restore
            try:
                data = json.loads(request.body)
                filename = data.get("filename")
                if not filename or ".." in filename or "/" in filename or "\\" in filename:
                    return JsonResponse({"error": "Invalid filename"}, status=400)
                
                backups_dir = os.path.join(settings.BASE_DIR, "backups")
                filepath = os.path.join(backups_dir, filename)
                if not os.path.exists(filepath):
                    return JsonResponse({"error": "File not found"}, status=404)
                
                call_command("restore_data", filepath, overwrite=overwrite)
                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# AI ADVISOR SETTINGS VIEWS (Phase 1 Infrastructure)
# ══════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class AISettingsView(AdminRequiredMixin, View):
    def get(self, request):
        enabled_str = AppSettings.get("ai_enabled", "false").strip().lower()
        enabled = enabled_str in ("true", "1", "yes")

        provider = AppSettings.get("ai_provider", "ollama").strip()
        ollama_url = AppSettings.get("ai_ollama_url", "http://localhost:11434").strip()
        model = AppSettings.get("ai_model", "llama3.2:latest").strip()

        try:
            temperature = float(AppSettings.get("ai_temperature", "0.7"))
        except (ValueError, TypeError):
            temperature = 0.7

        try:
            context_size = int(AppSettings.get("ai_context_size", "4096"))
        except (ValueError, TypeError):
            context_size = 4096

        try:
            timeout = int(AppSettings.get("ai_timeout", "15"))
        except (ValueError, TypeError):
            timeout = 15

        system_prompt = AppSettings.get(
            "ai_system_prompt", "You are a helpful financial advisor assistant."
        ).strip()

        try:
            max_tokens = int(AppSettings.get("ai_max_tokens", "2048"))
        except (ValueError, TypeError):
            max_tokens = 2048

        try:
            top_p = float(AppSettings.get("ai_top_p", "0.9"))
        except (ValueError, TypeError):
            top_p = 0.9

        try:
            top_k = int(AppSettings.get("ai_top_k", "40"))
        except (ValueError, TypeError):
            top_k = 40

        try:
            repeat_penalty = float(AppSettings.get("ai_repeat_penalty", "1.1"))
        except (ValueError, TypeError):
            repeat_penalty = 1.1

        seed = AppSettings.get("ai_seed", "").strip()
        keep_alive = AppSettings.get("ai_keep_alive", "5m").strip()

        return JsonResponse({
            "ai_enabled": enabled,
            "ai_provider": provider,
            "ai_ollama_url": ollama_url,
            "ai_model": model,
            "ai_temperature": temperature,
            "ai_context_size": context_size,
            "ai_timeout": timeout,
            "ai_system_prompt": system_prompt,
            "ai_max_tokens": max_tokens,
            "ai_top_p": top_p,
            "ai_top_k": top_k,
            "ai_repeat_penalty": repeat_penalty,
            "ai_seed": seed,
            "ai_keep_alive": keep_alive,
        })

    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        provider = str(data.get("ai_provider", "ollama")).strip().lower()
        if provider not in AVAILABLE_AI_PROVIDERS:
            return JsonResponse(
                {"error": f"Invalid provider '{provider}'. Must be one of {list(AVAILABLE_AI_PROVIDERS.keys())}"},
                status=400,
            )

        try:
            temperature = float(data.get("ai_temperature", 0.7))
            if not (0.0 <= temperature <= 2.0):
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_temperature must be a float between 0.0 and 2.0"}, status=400)

        try:
            context_size = int(data.get("ai_context_size", 4096))
            if context_size <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_context_size must be a positive integer"}, status=400)

        try:
            timeout = int(data.get("ai_timeout", 15))
            if timeout <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_timeout must be a positive integer"}, status=400)

        try:
            max_tokens = int(data.get("ai_max_tokens", 2048))
            if max_tokens <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_max_tokens must be a positive integer"}, status=400)

        try:
            top_p = float(data.get("ai_top_p", 0.9))
            if not (0.0 <= top_p <= 1.0):
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_top_p must be a float between 0.0 and 1.0"}, status=400)

        try:
            top_k = int(data.get("ai_top_k", 40))
            if top_k <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_top_k must be a positive integer"}, status=400)

        try:
            repeat_penalty = float(data.get("ai_repeat_penalty", 1.1))
            if repeat_penalty <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "ai_repeat_penalty must be a positive number"}, status=400)

        enabled = bool(data.get("ai_enabled", False))
        ollama_url = str(data.get("ai_ollama_url", "http://localhost:11434")).strip()
        model = str(data.get("ai_model", "llama3.2:latest")).strip()
        system_prompt = str(data.get("ai_system_prompt", "You are a helpful financial advisor assistant.")).strip()
        seed = str(data.get("ai_seed", "")).strip()
        keep_alive = str(data.get("ai_keep_alive", "5m")).strip()

        AppSettings.set("ai_enabled", "true" if enabled else "false")
        AppSettings.set("ai_provider", provider)
        AppSettings.set("ai_ollama_url", ollama_url)
        AppSettings.set("ai_model", model)
        AppSettings.set("ai_temperature", str(temperature))
        AppSettings.set("ai_context_size", str(context_size))
        AppSettings.set("ai_timeout", str(timeout))
        AppSettings.set("ai_system_prompt", system_prompt)
        AppSettings.set("ai_max_tokens", str(max_tokens))
        AppSettings.set("ai_top_p", str(top_p))
        AppSettings.set("ai_top_k", str(top_k))
        AppSettings.set("ai_repeat_penalty", str(repeat_penalty))
        AppSettings.set("ai_seed", seed)
        AppSettings.set("ai_keep_alive", keep_alive)

        # Run connection test post-save to report connection status
        connection_ok = False
        test_error = None
        if enabled:
            provider_inst = get_ai_provider(provider, base_url=ollama_url, model=model, timeout=timeout)
            if provider_inst:
                conn_res = provider_inst.check_connection()
                model_avail = provider_inst.check_model_available(model)
                connection_ok = bool(conn_res.get("reachable")) and model_avail
                test_error = conn_res.get("error") if not conn_res.get("reachable") else (None if model_avail else "Model not found")

        message_key = "ai_save_success" if (not enabled or connection_ok) else "ai_save_success_test_failed"

        return JsonResponse({
            "ok": True,
            "connection_ok": connection_ok,
            "message_key": message_key,
            "test_error": test_error,
        })


@method_decorator(csrf_exempt, name="dispatch")
class AIConnectionTestView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            data = {}

        provider_key = str(data.get("provider") or AppSettings.get("ai_provider", "ollama")).strip().lower()
        base_url = str(data.get("base_url") or AppSettings.get("ai_ollama_url", "http://localhost:11434")).strip()
        model = str(data.get("model") or AppSettings.get("ai_model", "llama3.2:latest")).strip()

        try:
            timeout = int(data.get("timeout") or AppSettings.get("ai_timeout", "15"))
        except (ValueError, TypeError):
            timeout = 15

        provider_inst = get_ai_provider(provider_key, base_url=base_url, model=model, timeout=timeout)
        if not provider_inst:
            return JsonResponse({
                "ok": False,
                "message_key": "ai_provider_invalid",
                "reachable": False,
                "version": None,
                "error": f"Invalid provider '{provider_key}'",
                "response_time_ms": 0,
                "models": [],
                "model_available": False,
            }, status=400)

        conn_res = provider_inst.check_connection()
        models = provider_inst.list_models()
        model_avail = provider_inst.check_model_available(model)

        reachable = bool(conn_res.get("reachable"))
        ok = reachable and model_avail

        return JsonResponse({
            "ok": ok,
            "message_key": "ai_connection_success" if ok else "ai_connection_failed",
            "reachable": reachable,
            "version": conn_res.get("version"),
            "error": conn_res.get("error"),
            "response_time_ms": conn_res.get("response_time_ms", 0),
            "models": models,
            "model_available": model_avail,
        }, status=200 if ok else 400)


@method_decorator(csrf_exempt, name="dispatch")
class AIProviderListView(AdminRequiredMixin, View):
    def get(self, request):
        providers = [
            {"key": k, "label_key": f"ai_provider_{k}"}
            for k in AVAILABLE_AI_PROVIDERS.keys()
        ]
        return JsonResponse({"providers": providers})


