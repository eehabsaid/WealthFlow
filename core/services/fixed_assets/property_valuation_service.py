from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib import parse

from django.db import transaction
from django.utils import timezone

from core.models import AppSettings, FixedAsset, RealEstateDetails
from core.services.fixed_assets.valuation_history_service import record_valuation_history

@dataclass
class PropertyValuationResult:
    processed_assets: int = 0
    updated_assets: int = 0
    skipped_assets: int = 0

    def to_dict(self):
        return {
            "processed_assets": self.processed_assets,
            "updated_assets": self.updated_assets,
            "skipped_assets": self.skipped_assets,
        }

class BasePropertyValuationProvider:
    name = "base"

    def estimate(self, asset: FixedAsset, details: RealEstateDetails) -> Optional[float]:
        return None

class ConfiguredMarketRateProvider(BasePropertyValuationProvider):
    name = "configured_market_rate"

    def estimate(self, asset: FixedAsset, details: RealEstateDetails) -> Optional[float]:
        area = float(details.area_m2 or 0)
        if area <= 0:
            return None

        config = self._load_config()
        if not config:
            return None

        district = str(details.district or "").strip()
        city = str(details.city or "").strip()
        governorate = str(details.governorate or "").strip()

        rate = None
        by_city = config.get("by_city") or {}
        by_governorate = config.get("by_governorate") or {}

        if district:
            rate = self._iget(by_city, district)
        if rate in (None, "") and city:
            rate = self._iget(by_city, city)
        if rate in (None, "") and governorate:
            rate = self._iget(by_governorate, governorate)
        if rate in (None, ""):
            rate = config.get("default")

        try:
            rate_value = float(rate)
        except (TypeError, ValueError):
            return None

        if rate_value <= 0:
            return None

        return round(area * rate_value, 2)

    def _normalize_location(self, s: str) -> str:
        if not s:
            return ""
        s = s.strip().lower()
        arabic_diacritics = [
            "\u064b", "\u064c", "\u064d", "\u064e", "\u064f", "\u0650", "\u0651", "\u0652"
        ]
        for d in arabic_diacritics:
            s = s.replace(d, "")
        s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        s = s.replace("ة", "ه").replace("ى", "ي")
        return s

    def _iget(self, mapping: dict, key: str):
        """Flexible dict lookup supporting case-insensitivity, Arabic/English bilingual aliases,
        and slash/comma separated multi-key entries.
        """
        if not key or not mapping:
            return None

        if key in mapping:
            return mapping[key]

        key_clean = str(key).strip()
        key_norm = self._normalize_location(key_clean)

        for k, v in mapping.items():
            if self._normalize_location(str(k)) == key_norm:
                return v

        LOCATION_ALIASES = {
            "cairo": {"cairo", "القاهرة", "القاهره", "el cairo", "cairo city"},
            "giza": {"giza", "الجيزة", "الجيزه", "el giza", "el giza governorate"},
            "alexandria": {"alexandria", "الإسكندرية", "الاسكندرية", "الإسكندريه", "الاسكندريه", "alex"},
            "sharm el sheikh": {"sharm el sheikh", "sharm el-sheikh", "شرم الشيخ", "شرم"},
            "hurghada": {"hurghada", "الغردقة", "الغردقه"},
            "luxor": {"luxor", "الأقصر", "الاقصر"},
            "aswan": {"aswan", "أسوان", "اسوان"},
            "mansoura": {"mansoura", "المنصورة", "المنصوره", "el mansoura"},
            "tanta": {"tanta", "طنطا"},
            "port said": {"port said", "بورسعيد", "بور سعيد"},
            "ismailia": {"ismailia", "الإسماعيلية", "الاسماعيلية", "الإسماعيليه", "الاسماعيليه"},
            "suez": {"suez", "السويس"},
            "dakahlia": {"dakahlia", "الدقهلية", "الدقهليه"},
            "sharqia": {"sharqia", "الشرقية", "الشرقيه"},
            "gharbia": {"gharbia", "الغربية", "الغربيه"},
            "monufia": {"monufia", "المنوفية", "المنوفيه"},
            "beheira": {"beheira", "البحيرة", "البحيره"},
            "qalyubia": {"qalyubia", "القليوبية", "القليوبيه"},
            "kafr el sheikh": {"kafr el sheikh", "كفر الشيخ"},
            "minya": {"minya", "المنيا"},
            "beni suef": {"beni suef", "بني سويف"},
            "fayoum": {"fayoum", "الفيوم"},
            "sohag": {"sohag", "سوهاج"},
            "qena": {"qena", "قنا"},
            "red sea": {"red sea", "البحر الأحمر", "البحر الاحمر"},
            "matrouh": {"matrouh", "مطروح", "مرسى مطروح", "marsa matrouh"},
            "north sinai": {"north sinai", "شمال سيناء"},
            "south sinai": {"south sinai", "جنوب سيناء"},
            "new valley": {"new valley", "الوادي الجديد"},
            "damietta": {"damietta", "دمياط"},
            "assiut": {"assiut", "أسيوط", "اسيوط"},
            "6th of october": {"6th of october", "6 october", "السادس من أكتوبر", "6 أكتوبر", "أكتوبر", "اكتوبر"},
            "sheikh zayed": {"sheikh zayed", "الشيخ زايد", "زايد"},
            "new cairo": {"new cairo", "القاهرة الجديدة"},
            "fifth settlement": {"fifth settlement", "5th settlement", "التجمع الخامس", "التجمع"},
            "nasr city": {"nasr city", "مدينة نصر"},
            "heliopolis": {"heliopolis", "مصر الجديدة"},
            "maadi": {"maadi", "el maadi", "المعادي"},
            "zamalek": {"zamalek", "الزمالك"},
            "wadi hoff": {"wadi hoff", "wadi hof", "وادي حوف"},
            "helwan": {"helwan", "حلوان"},
            "mokattam": {"mokattam", "المقطم"},
            "dokki": {"dokki", "الدقي"},
            "mohandessin": {"mohandessin", "mohandseen", "المهندسين"},
            "new administrative capital": {"new administrative capital", "administrative capital", "العاصمة الإدارية", "العاصمة الإدارية الجديدة", "العاصمه الاداريه"},
            "new alamein": {"new alamein", "alamein", "العلمين الجديدة", "العلمين"},
            "north coast": {"north coast", "الساحل الشمالي", "الساحل"},
        }

        input_aliases = {key_norm}
        for alias_group in LOCATION_ALIASES.values():
            normalized_group = {self._normalize_location(item) for item in alias_group}
            if key_norm in normalized_group:
                input_aliases.update(normalized_group)
                break

        for k, v in mapping.items():
            parts = [p.strip() for p in re.split(r"[/,\|]", str(k)) if p.strip()]
            for part in parts:
                part_norm = self._normalize_location(part)
                if part_norm in input_aliases:
                    return v

                for alias_group in LOCATION_ALIASES.values():
                    normalized_group = {self._normalize_location(item) for item in alias_group}
                    if part_norm in normalized_group and (normalized_group & input_aliases):
                        return v

                if len(part_norm) >= 3 and len(key_norm) >= 3:
                    if part_norm in key_norm or key_norm in part_norm:
                        return v

        return None

    def _load_config(self):
        raw = AppSettings.get("property_valuation_rate_map", "")
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

class ExternalApiPropertyValuationProvider(BasePropertyValuationProvider):
    name = "external_api"

    def estimate(self, asset: FixedAsset, details: RealEstateDetails) -> Optional[float]:
        config = self._load_config()
        if not config["enabled"]:
            return None

        url = self._build_url(config["url_template"], asset, details)
        if not url:
            return None

        payload = self._fetch_payload(
            url=url,
            timeout_seconds=config["timeout_seconds"],
            headers=config["headers"],
        )
        if payload is None:
            return None

        return self._extract_estimate(payload, config["result_path"])

    def _load_config(self):
        enabled_raw = str(AppSettings.get("property_valuation_external_enabled", "false") or "").strip().lower()
        timeout = self._safe_float(AppSettings.get("property_valuation_external_timeout_secs", "8"), 8.0)
        url_template = str(AppSettings.get("property_valuation_external_url", "") or "").strip()
        result_path = str(AppSettings.get("property_valuation_external_result_path", "estimated_price") or "estimated_price").strip()

        headers = {}
        headers_raw = str(AppSettings.get("property_valuation_external_headers", "") or "").strip()
        if headers_raw:
            try:
                parsed = json.loads(headers_raw)
                if isinstance(parsed, dict):
                    headers = {str(k): str(v) for k, v in parsed.items()}
            except (TypeError, ValueError, json.JSONDecodeError):
                headers = {}

        return {
            "enabled": enabled_raw in {"1", "true", "yes", "on"},
            "url_template": url_template,
            "result_path": result_path,
            "timeout_seconds": timeout if timeout > 0 else 8.0,
            "headers": headers,
        }

    def _build_url(self, template: str, asset: FixedAsset, details: RealEstateDetails) -> Optional[str]:
        if not template:
            return None

        city = str(details.city or "").strip()
        governorate = str(details.governorate or "").strip()
        district = str(details.district or "").strip()
        country = str(details.country or "").strip()
        area_m2 = float(details.area_m2 or 0)

        context = {
            "asset_id": asset.id,
            "asset_name": parse.quote(asset.name or ""),
            "city": parse.quote(city),
            "city_raw": city,
            "governorate": parse.quote(governorate),
            "governorate_raw": governorate,
            "district": parse.quote(district),
            "district_raw": district,
            "country": parse.quote(country),
            "country_raw": country,
            "area_m2": area_m2,
        }
        try:
            return template.format(**context)
        except (KeyError, ValueError):
            return None

    def _fetch_payload(self, url: str, timeout_seconds: float, headers: dict):
        from core.integrations import fetch_property_external_valuation
        return fetch_property_external_valuation(url, timeout_seconds, headers)

    def _extract_estimate(self, payload, result_path: str) -> Optional[float]:
        if isinstance(payload, (int, float)):
            return self._coerce_positive_float(payload)

        if result_path:
            by_path = self._read_path(payload, result_path)
            estimated = self._coerce_positive_float(by_path)
            if estimated is not None:
                return estimated

        for candidate in [
            "estimated_price",
            "estimate",
            "market_price",
            "price",
            "value",
            "data.estimated_price",
            "data.estimate",
            "result.estimated_price",
        ]:
            value = self._read_path(payload, candidate)
            estimated = self._coerce_positive_float(value)
            if estimated is not None:
                return estimated

        return None

    def _read_path(self, payload, path: str):
        current = payload
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
                continue
            if isinstance(current, list) and part.isdigit():
                index = int(part)
                if index >= len(current):
                    return None
                current = current[index]
                continue
            return None
        return current

    def _coerce_positive_float(self, value) -> Optional[float]:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        return round(parsed, 2)

    def _safe_float(self, value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

class PropertyValuationService:
    """Abstracted property valuation pipeline.

    The first shipped provider is intentionally conservative: if a reliable estimate
    is not available, the service leaves the manual market value unchanged.
    """

    def __init__(self, providers=None):
        self.providers = providers or self._build_default_providers()

    def _build_default_providers(self):
        provider_map = {
            "external_api": ExternalApiPropertyValuationProvider(),
            "configured_market_rate": ConfiguredMarketRateProvider(),
        }

        order_raw = str(
            AppSettings.get(
                "property_valuation_provider_order",
                "external_api,configured_market_rate",
            )
            or ""
        )
        resolved = []
        for name in [item.strip().lower() for item in order_raw.split(",") if item.strip()]:
            provider = provider_map.get(name)
            if provider and provider not in resolved:
                resolved.append(provider)

        if not resolved:
            resolved.append(provider_map["configured_market_rate"])
        return resolved

    def refresh_asset(self, asset: FixedAsset, today=None):
        details = getattr(asset, "real_estate", None)
        if not details:
            return False, None

        for provider in self.providers:
            estimate = provider.estimate(asset, details)
            if estimate is None:
                continue
            self._store_estimate(asset, details, provider.name, estimate, today=today)
            return True, provider.name

        return False, None

    def refresh_all(self, today=None):
        result = PropertyValuationResult()
        assets = FixedAsset.objects.select_related("real_estate").filter(asset_type="Real Estate")
        with transaction.atomic():
            for asset in assets:
                result.processed_assets += 1
                updated, _ = self.refresh_asset(asset, today=today)
                if updated:
                    result.updated_assets += 1
                else:
                    result.skipped_assets += 1
        return result

    def _store_estimate(self, asset, details, provider_name, estimate, today=None):
        valuation_date = today or timezone.localdate()
        details.last_estimated_market_price = estimate
        details.last_valuation_date = valuation_date
        details.valuation_provider = provider_name
        details.save(update_fields=["last_estimated_market_price", "last_valuation_date", "valuation_provider", "updated_at"])
        asset.current_market_value = estimate
        asset.valuation_source = "Automatic"
        asset.last_valuation_date = valuation_date
        asset.save(update_fields=["current_market_value", "valuation_source", "last_valuation_date"])

        record_valuation_history(
            asset,
            market_value=estimate,
            source="Automatic",
            valuation_date=valuation_date,
            notes=f"Auto-synced via {provider_name}",
        )
