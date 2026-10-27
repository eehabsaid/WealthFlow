"""Fits a JSON answer into the room a tool result has, by shortening the longest lists and texts first and saying so."""

from __future__ import annotations

import json
from typing import Any

LIST_CAPS = (60, 30, 15, 8, 4)
TEXT_CAP = 300


def _size(data: Any) -> int:
    return len(json.dumps(data, default=str, ensure_ascii=False, separators=(",", ":")))


def _cut(data: Any, cap: int, notes: list, where: str = "") -> Any:
    if isinstance(data, dict):
        return {k: _cut(v, cap, notes, f"{where}.{k}" if where else str(k)) for k, v in data.items()}
    if isinstance(data, list):
        kept = [_cut(v, cap, notes, f"{where}[]") for v in data[:cap]]
        if len(data) > cap:
            notes.append(f"{where or 'list'}: first {cap} of {len(data)} items")
        return kept
    if isinstance(data, str) and len(data) > TEXT_CAP:
        notes.append(f"{where or 'text'}: text shortened")
        return data[:TEXT_CAP] + "…"
    return data


def fit(data: Any, limit: int) -> tuple[Any, list[str]]:
    """(data that fits `limit` characters, what was shortened). Nothing is changed when it already fits."""
    if _size(data) <= limit:
        return data, []
    for cap in LIST_CAPS:
        notes: list[str] = []
        cut = _cut(data, cap, notes)
        if _size(cut) <= limit:
            return cut, sorted(set(notes))
    shape = {k: (f"list of {len(v)}" if isinstance(v, list) else "object" if isinstance(v, dict) else v) for k, v in data.items()} \
        if isinstance(data, dict) else f"list of {len(data)}" if isinstance(data, list) else str(data)[:limit]
    return {"too_large_overview": shape}, ["too large: narrow the call with query parameters (dates, ids, filters)"]
