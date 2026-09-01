from __future__ import annotations

import json
import re
from typing import Optional

from core.models import AppSettings, FixedAsset, RealEstateDetails

from .base import BasePropertyValuationProvider


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
