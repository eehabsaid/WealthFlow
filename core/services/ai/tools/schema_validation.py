"""Generic schema-driven parameter coercion/validation for AI tool calls (backlog item 3).

Small local models routinely emit "false", "5" or '["1","2"]' (strings) where the tool
schema says boolean/integer/array. Before this, only required-ness was checked, and
handlers did `bool(params.get("force_refresh"))` -- so the string "false" was truthy and
triggered a live re-crawl. Coerce what is unambiguous, reject what is not, keep unknown
parameters untouched (handlers read a few that are not in the schema)."""

from __future__ import annotations

import json
import re
from typing import Any

_TRUE = {"true", "yes", "1", "y"}
_FALSE = {"false", "no", "0", "n", ""}
_INT = re.compile(r"^[+-]?\d+$")
_MISSING = object()


def as_bool(value: Any, default: bool = False) -> bool:
    """Tolerant boolean for handler-side flags that are not in a tool's schema."""
    if value is None:
        return default
    if isinstance(value, str):
        low = value.strip().lower()
        return True if low in _TRUE else False if low in _FALSE else default
    return bool(value)


def _coerce(value: Any, spec: dict[str, Any]) -> Any:
    """Returns the coerced value, or _MISSING when it cannot be coerced to spec's type."""
    typ = spec.get("type")
    if typ == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in _TRUE | _FALSE:
            return value.strip().lower() in _TRUE
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        return _MISSING
    if typ == "integer":
        if isinstance(value, bool):
            return _MISSING
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and _INT.match(value.strip()):
            return int(value.strip())
        return _MISSING
    if typ == "number":
        if isinstance(value, bool):
            return _MISSING
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return _MISSING
        return _MISSING
    if typ == "string":
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return _MISSING
    if typ in ("array", "object"):
        want = list if typ == "array" else dict
        if isinstance(value, str) and value.strip()[:1] in ("[", "{"):
            try:
                value = json.loads(value)
            except ValueError:
                return _MISSING
        if not isinstance(value, want):
            return _MISSING
        item_spec = spec.get("items")
        if typ == "array" and isinstance(item_spec, dict) and item_spec.get("type") in ("integer", "number", "boolean", "string"):
            items = [_coerce(v, item_spec) for v in value]
            return _MISSING if any(i is _MISSING for i in items) else items
        return value
    return value  # no/unknown declared type: leave as is


def coerce_and_validate(
    schema_params: dict[str, Any], params: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    """Returns (params_with_coerced_values, error_message_or_None)."""
    props = (schema_params or {}).get("properties") or {}
    out = dict(params)
    for key, spec in props.items():
        if key not in out or out[key] is None or not isinstance(spec, dict):
            continue
        val = _coerce(out[key], spec)
        if val is _MISSING:
            typ = spec.get("type", "valid value")
            return out, f"Parameter '{key}' must be of type {typ}"
        enum = spec.get("enum")
        if enum:
            match = next((e for e in enum if str(e).lower() == str(val).strip().lower()), _MISSING)
            if match is _MISSING:
                return out, f"Parameter '{key}' must be one of: {', '.join(str(e) for e in enum)}"
            val = match
        out[key] = val
    return out, None
