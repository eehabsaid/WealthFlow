"""Generic read-only business-data tools: model catalog + filter/sort/aggregate/group queries.

Always starts from scope.scoped_queryset (the current user's own rows). Filter keys are validated against the model's
real, non-sensitive fields (one FK hop allowed, e.g. `bank__name__icontains`), so the model cannot reach another user's
rows, a secret column or an arbitrary ORM expression. Errors list the valid names so the model can correct itself.
"""

from __future__ import annotations


from django.core.exceptions import FieldError, ValidationError

from ai.services.investigation import scope
from .data_tools_helpers import FOREIGN_KEY_QUERY_NOTE, MAX_GROUPS, MAX_ROWS, MODEL_CATALOG_NOTE, MODEL_NOTES, QueryError, _aggregates, _filters, _group_paths, _having_filters, _json_rows, _resolve, _walk, LOOKUPS, AGGREGATES, ROW_CHARS, _fields_hint, _coerce


def models(user, params):
    if params.get("model"):
        try:
            info = _resolve(params)
        except QueryError as exc:
            return {"error": str(exc)}
        fields = [{"name": f.name, "type": type(f).__name__,
                   **({"relates_to": f.related_model.__name__,
                       "related_fields": [related.name for related in scope.visible_fields(f.related_model)]
                       } if f.is_relation and f.related_model and f.related_model.__name__ in scope.catalog() else {}),
                   **({"choices": [c[0] for c in f.choices][:12]} if getattr(f, "choices", None) else {})}
                  for f in scope.visible_fields(info.model)]
        return {
            "model": info.name,
            "label": str(info.model._meta.verbose_name),
            "rows": scope.scoped_queryset(info, user).count(),
            "fields": fields,
            **({"note": MODEL_NOTES[info.name]} if info.name in MODEL_NOTES else {}),
        }
    return {"models": [{"model": i.name, "rows": scope.scoped_queryset(i, user).count(),
                        "label": str(i.model._meta.verbose_name),
                        "fields": [f.name for f in scope.visible_fields(i.model)],
                        **({"note": MODEL_NOTES[i.name]} if i.name in MODEL_NOTES else {})}
                       for i in scope.catalog().values()],
            "note": f"{MODEL_CATALOG_NOTE} Call app_data_models with model=<name> for field types and related fields."}


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
                paths = _group_paths(model, group)
                grouped = qs.values(*paths).annotate(**aggs)
                if params.get("having"):
                    grouped = grouped.filter(**_having_filters(params["having"], aggs))
                rows = list(grouped.order_by(*paths)[:MAX_GROUPS + 1])
                out = {"model": info.name, "group_by": group, "groups": rows[:MAX_GROUPS],
                       "group_count": min(len(rows), MAX_GROUPS)}
                if len(rows) > MAX_GROUPS:
                    out["note"] = "more groups exist: narrow filters or add a having filter"
                return out
            if params.get("having"):
                raise QueryError("having requires group_by")
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
        return {"error": f"query rejected: {str(exc)[:200]}. Check field names/value types with app_data_models.{FOREIGN_KEY_QUERY_NOTE}"}
    out = {"model": info.name, "total_matching": total, "returned": len(rows), "rows": rows}
    if cut or total > len(rows):
        out["note"] = "more rows exist: narrow filters, raise limit (max 100) or use aggregate/group_by for totals"
    return out


__all__ = [
    "FOREIGN_KEY_QUERY_NOTE",
    "MAX_GROUPS",
    "MAX_ROWS",
    "MODEL_CATALOG_NOTE",
    "MODEL_NOTES",
    "QueryError",
    "_aggregates",
    "_filters",
    "_group_paths",
    "_having_filters",
    "_json_rows",
    "_resolve",
    "_walk",
    "LOOKUPS",
    "AGGREGATES",
    "ROW_CHARS",
    "_fields_hint",
    "_coerce",
    "models",
    "query",
]
