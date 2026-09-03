"""Constants for the Aqarmap scraper: district slugs, baselines, HTTP headers."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# District slug → display name
# Names must align with LOCATION_ALIASES in property_valuation_service.py
# ---------------------------------------------------------------------------
DISTRICT_PATHS: dict[str, str] = {
    "zamalek": "Zamalek",
    "garden-city": "Garden City",
    "maadi": "Maadi",
    "heliopolis": "Heliopolis",
    "nasr-city": "Nasr City",
    "new-cairo": "New Cairo",
    "dokki": "Dokki",
    "mohandessin": "Mohandessin",
    "6th-of-october": "6th of October",
    "el-sheikh-zayed-city": "Sheikh Zayed",
    "new-administrative-capital": "New Administrative Capital",
    "mokattam": "Mokattam",
    "helwan": "Helwan",
    "shubra": "Shubra",
    "ain-shams": "Ain Shams",
    "hadayek-el-kobba": "Hadayek el Kobba",
    "abbassia": "Abbassia",
    "downtown-cairo": "Downtown Cairo",
    "madinaty": "Madinaty",
    "el-shorouk": "Shorouk",
    "badr-city": "Badr City",
    "el-obour": "Obour",
    "agouza": "Agouza",
    "imbaba": "Imbaba",
    "el-matariya": "Matariya",
    "boulaq": "Boulaq",
    "helwan/wdy-hwf": "Wadi Hof",   # Cairo > Helwan > Wadi Hof
}

BASE_URL = "https://aqarmap.com.eg/en/for-sale/property-type/cairo/{path}/"

# ---------------------------------------------------------------------------
# Baseline — used for missing/invalid districts
# ---------------------------------------------------------------------------
CAIRO_BASELINE: dict[str, float] = {
    "Zamalek": 95_000,
    "Garden City": 75_000,
    "Maadi": 55_000,
    "Heliopolis": 52_000,
    "Dokki": 52_000,
    "Mohandessin": 52_000,
    "Fifth Settlement": 48_000,
    "Agouza": 48_000,
    "New Cairo": 45_000,
    "New Administrative Capital": 40_000,
    "Sheikh Zayed": 35_000,
    "Downtown Cairo": 35_000,
    "Nasr City": 32_000,
    "Madinaty": 38_000,
    "Shorouk": 30_000,
    "6th of October": 27_000,
    "Mokattam": 27_000,
    "Hadayek el Kobba": 28_000,
    "Abbassia": 24_000,
    "Badr City": 22_000,
    "Shubra": 22_000,
    "Obour": 20_000,
    "Boulaq": 20_000,
    "Ain Shams": 18_000,
    "Imbaba": 18_000,
    "Matariya": 16_000,
    "Wadi Hof": 22_000,
    "Helwan": 22_000,
}

GOVERNORATE_BASELINE: dict[str, float] = {
    "Cairo": 35_000,
    "Giza": 28_000,
    "Alexandria": 25_000,
    "North Coast": 30_000,
    "Sharm El Sheikh": 40_000,
    "Hurghada": 22_000,
    "Mansoura": 12_000,
    "Tanta": 10_000,
    "Port Said": 14_000,
    "Ismailia": 12_000,
    "Suez": 11_000,
    "Luxor": 9_000,
    "Aswan": 8_000,
    "New Valley": 7_000,
}

DEFAULT_RATE: float = 20_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

_MIN_RATE = 3_000
_MAX_RATE = 500_000
