"""Dataset spec -> markdown table, straight from the database (the model never types the numbers).

Reuses the investigator's validated query layer: scope.scoped_queryset starts every query from the given user's own
rows, field / filter names are checked against real, non-sensitive fields, so owner isolation is identical to
app_data_query. Differences: no 100-row cap (up to the `ai_file_max_rows` setting) and plain rows instead of JSON."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import FieldError, ValidationError

from core.services.ai.investigation import data_tools as dt, scope

SKIP_DEFAULT = {"id", "created_at", "updated_at"}
MAX_DEFAULT_COLUMNS = 30


class DatasetError(ValueError):
    """A spec problem the model can fix (the message lists the valid names)."""


def cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (Decimal, float)):
        return f"{float(value):,.2f}"
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, (datetime.date, int)):
        return str(value)
    text = " ".join(str(value).replace("|", "/").split())
    return text if len(text) <= 500 else text[:499] + "…"


def _as_list(value: Any) -> list:
    if value in (None, ""):
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _readable(model, name: str) -> str:
    """A plain foreign key becomes its `name` column so the file shows words, not ids."""
    try:
        field = model._meta.get_field(name.removesuffix("_id"))
    except Exception:
        return name
    related = getattr(field, "related_model", None)
    if field.is_relation and field.many_to_one and related is not None and any(f.name == "name" for f in related._meta.concrete_fields):
        return f"{field.name}__name"
    return name


def _label(model, path: str, labels: dict) -> str:
    if path in labels:
        return str(labels[path])
    try:
        return str(model._meta.get_field(path.split("__")[0].removesuffix("_id")).verbose_name).strip().capitalize()
    except Exception:
        return path


def _query(user: Any, spec: dict, max_rows: int):
    info = dt._resolve(spec)
    model = info.model
    qs = scope.scoped_queryset(info, user)
    if spec.get("filters"):
        qs = qs.filter(**dt._filters(model, spec["filters"]))
    limit = max(1, min(max_rows, int(spec["limit"]))) if spec.get("limit") else max_rows
    total = qs.count()
    if spec.get("aggregate") or spec.get("group_by"):
        groups = [dt._walk(model, str(g), False)[0] for g in _as_list(spec.get("group_by"))]
        aggs = dt._aggregates(model, spec.get("aggregate") or {"count": "*"})
        if groups:
            names = groups + list(aggs)
            rows = [[r[n] for n in names] for r in qs.values(*groups).annotate(**aggs).order_by(*groups)[:limit]]
        else:
            result = qs.aggregate(**aggs)
            names, rows = list(aggs), [[result[n] for n in aggs]]
        return info, model, names, rows, len(rows)
    requested = [str(f) for f in _as_list(spec.get("fields"))] or \
        [f.name for f in scope.visible_fields(model) if f.name not in SKIP_DEFAULT][:MAX_DEFAULT_COLUMNS]
    names = [dt._walk(model, _readable(model, f), False)[0] for f in requested]
    order = [("-" if str(o).startswith("-") else "") + dt._walk(model, str(o).lstrip("-"), False)[0] for o in _as_list(spec.get("order_by"))]
    return info, model, names, [list(r) for r in qs.order_by(*order).values_list(*names)[:limit]], total


def _totals(columns: list, names: list, rows: list, wanted: list) -> list | None:
    """Bold last row summing the requested numeric columns (matched by header or field name)."""
    if not wanted or not rows:
        return None
    keys = {str(w).lower() for w in wanted}
    num = lambda v: isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)   # noqa: E731
    out = []
    for i, (col, name) in enumerate(zip(columns, names)):
        summed = bool(keys & {str(col).lower(), name.lower()}) and any(num(r[i]) for r in rows)
        out.append(float(sum(r[i] for r in rows if num(r[i]))) if summed else "")
    for i, value in enumerate(out):
        if value == "":
            out[i] = "Total"
            break
    return out


def dataset_markdown(user: Any, spec: dict, max_rows: int, title: str = "") -> tuple[str, int]:
    """(markdown with a heading and one table, row count). Raises DatasetError with the valid names on a bad spec."""
    if not isinstance(spec, dict):
        raise DatasetError("dataset must be an object: {model, filters, fields, order_by, group_by, aggregate, total_columns, labels, limit}")
    try:
        info, model, names, rows, total = _query(user, spec, max_rows)
    except dt.QueryError as exc:
        raise DatasetError(str(exc)) from exc
    except (FieldError, ValidationError, ValueError, TypeError) as exc:
        raise DatasetError(f"dataset rejected: {str(exc)[:200]}. Check the names with app_data_models.") from exc
    labels = spec.get("labels") if isinstance(spec.get("labels"), dict) else {}
    columns = [_label(model, n, labels) for n in names]
    totals = _totals(columns, names, rows, _as_list(spec.get("total_columns")))
    lines = [f"## {title or spec.get('title') or info.name}", "", "| " + " | ".join(cell_text(c) for c in columns) + " |",
             "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell_text(v) for v in r) + " |" for r in rows]
    if totals:
        lines.append("| " + " | ".join(f"**{cell_text(v)}**" if v != "" else "" for v in totals) + " |")
    if not spec.get("aggregate") and not spec.get("group_by") and total > len(rows):
        lines += ["", f"Showing {len(rows)} of {total} matching rows."]
    return "\n".join(lines), len(rows)
