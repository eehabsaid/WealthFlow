"""Next.js RSC payload decoding and averagePriceData extraction/validation."""

from __future__ import annotations

import json
import re
from typing import Optional

from .constants import _MIN_RATE, _MAX_RATE


def _decode_rsc(html: str) -> str:
    """Concatenate all self.__next_f.push([1, '...']) payloads."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', html, re.DOTALL)
    out = ""
    for c in chunks:
        try:
            out += json.loads(c)
        except Exception:
            pass
    return out


def _extract_avg_price_data(rsc_text: str) -> Optional[dict]:
    """Extract the averagePriceData JSON object from RSC text."""
    idx = rsc_text.find('"averagePriceData"')
    if idx < 0:
        return None
    brace_start = rsc_text.find('{', idx)
    if brace_start < 0:
        return None
    depth = 0
    for i, ch in enumerate(rsc_text[brace_start:], brace_start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(rsc_text[brace_start:i + 1])
                except Exception:
                    return None
    return None


def _latest_apartment_price(avg_data: dict) -> Optional[float]:
    """Return the most recent valid apartment (type '1') price per sqm."""
    try:
        entries = avg_data["data"]["1"]["data"]["average_price"]
        valid = [
            float(e["value"])
            for e in entries
            if _MIN_RATE <= float(e["value"]) <= _MAX_RATE
        ]
        return valid[-1] if valid else None
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def _slug_matches(avg_data: dict, requested_slug: str) -> bool:
    """
    Validate that Aqarmap returned data for the district we requested,
    not a redirect to the city-wide page.

    When a slug doesn't exist, Aqarmap silently redirects to the main
    Cairo page whose averagePriceData.location.slug == "cairo".
    We reject that and fall back to baseline for that district.
    """
    returned_slug = avg_data.get("location", {}).get("slug", "")
    return returned_slug.endswith(requested_slug)
