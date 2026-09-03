"""
Aqarmap EGP/sqm scraper for Cairo districts.

Fetches https://aqarmap.com.eg/en/for-sale/property-type/cairo/{path}/
for each known district, parses the Next.js RSC payload, and extracts
averagePriceData → latest apartment price per sqm.

KEY VALIDATION: the returned averagePriceData.location.slug must end
with the requested slug. If it doesn't, Aqarmap redirected to the
city-wide page (returning the Cairo default ~27,100) — that value is
discarded and baseline is used instead.

source values:
  "aqarmap_live+baseline"  → live data merged with baseline gaps
  "baseline_only"          → scraping failed or skipped

Sibling modules:
- constants.py: DISTRICT_PATHS, BASE_URL, CAIRO_BASELINE, GOVERNORATE_BASELINE, DEFAULT_RATE, headers, rate bounds
- rsc_parsing.py: RSC payload decode/extract/validate helpers
- district_scraper.py: live scraping loop across all districts (_scrape_districts)
- rate_map_builder.py: build_rate_map() public entry point
"""

from __future__ import annotations

from .constants import CAIRO_BASELINE, GOVERNORATE_BASELINE, DEFAULT_RATE, DISTRICT_PATHS
from .rate_map_builder import build_rate_map

__all__ = [
    "build_rate_map",
    "CAIRO_BASELINE",
    "GOVERNORATE_BASELINE",
    "DEFAULT_RATE",
    "DISTRICT_PATHS",
]
