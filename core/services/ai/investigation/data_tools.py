"""Generic read-only business-data tools: model catalog + filter/sort/aggregate/group queries.

Always starts from scope.scoped_queryset (the current user's own rows). Filter keys are validated against the model's
real, non-sensitive fields (one FK hop allowed, e.g. `bank__name__icontains`), so the model cannot reach another user's
rows, a secret column or an arbitrary ORM expression. Errors list the valid names so the model can correct itself.
"""

from __future__ import annotations

import json

from django.core.exceptions import FieldDoesNotExist, FieldError, ValidationError
from django.db.models import Avg, BooleanField, Count, Max, Min, Sum

from . import scope

LOOKUPS = frozenset({"exact", "iexact", "contains", "icontains", "startswith", "istartswith", "endswith", "gt", "gte",
                     "lt", "lte", "in", "isnull", "range", "year", "month", "day"})
AGGREGATES = {"sum": Sum, "avg": Avg, "min": Min, "max": Max}
MAX_ROWS, MAX_GROUPS, ROW_CHARS = 100, 50, 7000


class QueryError(ValueError):
    pass


def _fields_hint(model) -> str:
    return ", ".join(f.name for f in scope.visible_fields(model))


def _walk(model, path: str, allow_lookup: bool):
    """Validate `field[__relatedfield][__lookup]`; returns (django_path, final_field, lookup)."""
    parts = path.split("__")
    lookup = parts.pop() if allow_lookup and len(parts) > 1 and parts[-1] in LOOKUPS else None
    if not parts or len(parts) > 2:
        raise QueryError(f"bad field '{path}'; use field or fk_field__related_field. Fields: {_fields_hint(model)}")
    current, field = model, None
    for i, part in enumerate(parts):
        try:
            field = current._meta.get_field(part.removesuffix("_id") if part.endswith("_id") else part)
        except FieldDoesNotExist:
            raise QueryError(f"unknown field '{part}' on {current.__name__}. Fields: {_fields_hint(current)}") from None
        if not field.concrete or not scope.field_ok(field):
            raise QueryError(f"field '{part}' is not available on {current.__name__}. Fields: {_fields_hint(current)}")
        if i < len(parts) - 1:
            target = field.related_model if field.is_relation else None
            if target is None or target.__name__ not in scope.catalog():
                raise QueryError(f"'{part}' is not a relation to a readable table")
            current = target
    return "__".join(parts) + (f"__{lookup}" if lookup else ""), field, lookup


def _coerce(field, lookup, value):
    if lookup == "isnull":
        return str(value).lower() in ("true", "1", "yes")
    if lookup in ("in", "range"):
        items = value if isinstance(value, list) else [v.strip() for v in str(value).split(",")]
        if lookup == "range" and len(items) != 2:
            raise QueryError("range needs exactly two values [from, to]")
        return [_coerce(field, "exact", v) for v in items]
    if isinstance(field, BooleanField) and isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "t")
    return value


def _filters(model, raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except ValueError:
            raise QueryError("filters must be a JSON object such as {\"date__gte\": \"2026-09-01\"}") from None
    if not isinstance(raw, dict):
        raise QueryError("filters must be an object of {field__lookup: value}")
    out = {}
    for key, value in raw.items():
        path, field, lookup = _walk(model, str(key), True)
        out[path] = _coerce(field, lookup, value)
    return out


def _json_rows(rows: list) -> tuple[list, bool]:
    kept, used = [], 0
    for row in rows:
        size = len(json.dumps(row, default=str, ensure_ascii=False))
        if used + size > ROW_CHARS and kept:
            return kept, True
        kept.append(row)
        used += size
    return kept, False


def _aggregates(model, spec) -> dict:
    if not isinstance(spec, dict) or not spec:
        raise QueryError("aggregate must be like {\"sum\": \"amount\"} or {\"count\": \"*\"}")
    out = {}
    for fn, target in spec.items():
        fn = str(fn).lower()
        if fn == "count":
            out["count"] = Count("pk") if str(target) in ("*", "", "id", "pk") else Count(_walk(model, str(target), False)[0])
        elif fn in AGGREGATES:
            out[f"{fn}_{str(target).replace('__', '_')}"] = AGGREGATES[fn](_walk(model, str(target), False)[0])
        else:
            raise QueryError(f"unknown aggregate '{fn}'; use count, sum, avg, min, max")
    return out


def _resolve(params):
    info = scope.resolve_model(params.get("model"))
    if info is None:
        raise QueryError("unknown model '%s'. Queryable models: %s" % (params.get("model"), ", ".join(scope.catalog())))
    return info


def models(user, params):
    if params.get("model"):
        try:
            info = _resolve(params)
        except QueryError as exc:
            return {"error": str(exc)}
        fields = [{"name": f.name, "type": type(f).__name__,
                   **({"relates_to": f.related_model.__name__} if f.is_relation and f.related_model else {}),
                   **({"choices": [c[0] for c in f.choices][:12]} if getattr(f, "choices", None) else {})}
                  for f in scope.visible_fields(info.model)]
        return {"model": info.name, "rows": scope.scoped_queryset(info, user).count(), "fields": fields}
    return {"models": [{"model": i.name, "rows": scope.scoped_queryset(i, user).count(),
                        "fields": [f.name for f in scope.visible_fields(i.model)][:9]} for i in scope.catalog().values()],
            "note": "call app_data_models with model=<name> for every field, then app_data_query to read rows"}


def query(user, params):
    try:
        info = _resolve(params)
        qs = scope.scoped_queryset(info, user)
        model = info.model
        if params.get("filters"):
            qs = qs.filter(**_filters(model, params["filters"]))
        if params.get("aggregate"):
            aggs = _aggregates(model, params["aggregate"])
            group = params.get("group_by")
            if group:
                path = _walk(model, str(group), False)[0]
                rows = list(qs.values(path).annotate(**aggs).order_by(path)[:MAX_GROUPS])
                return {"model": info.name, "group_by": group, "groups": rows, "group_count": len(rows)}
            return {"model": info.name, "total_matching": qs.count(), "result": qs.aggregate(**aggs)}
        limit = max(1, min(MAX_ROWS, int(params.get("limit") or 25)))
        names = [_walk(model, str(f), False)[0] for f in (params.get("fields") or [])] or \
                [f.name for f in scope.visible_fields(model)][:14]
        order = [("-" if str(o).startswith("-") else "") + _walk(model, str(o).lstrip("-"), False)[0]
                 for o in (params.get("order_by") or [])]
        total = qs.count()
        rows, cut = _json_rows(list(qs.order_by(*order).values(*names)[:limit]) if order else list(qs.values(*names)[:limit]))
    except QueryError as exc:
        return {"error": str(exc)}
    except (FieldError, ValidationError, ValueError, TypeError) as exc:
        return {"error": f"query rejected: {str(exc)[:200]}. Check field names/value types with app_data_models."}
    out = {"model": info.name, "total_matching": total, "returned": len(rows), "rows": rows}
    if cut or total > len(rows):
        out["note"] = "more rows exist: narrow filters, raise limit (max 100) or use aggregate/group_by for totals"
    return out
