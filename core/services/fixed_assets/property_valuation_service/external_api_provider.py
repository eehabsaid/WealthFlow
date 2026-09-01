from __future__ import annotations

import json
from typing import Optional
from urllib import parse

from core.models import AppSettings, FixedAsset, RealEstateDetails

from .base import BasePropertyValuationProvider


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
