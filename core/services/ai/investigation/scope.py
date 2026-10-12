"""Which tables the AI may read for a user, and how each one is isolated by owner.

Direct tables have an `owner` FK to the user. Others (salary, rentals, asset sub-records ...) are isolated through the
shortest FK/OneToOne chain to an owned parent (e.g. SalaryEntry -> `company__owner`). Market data and plan catalogs
carry no personal data and are readable as-is. Credentials, auth/permission tables, AI internals, settings and
documents are never exposed. Anything that is neither owner-scoped nor on the global list is not queryable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from django.apps import apps
from django.conf import settings

GLOBAL_MODELS = frozenset({"ExchangeRate", "ExchangeRateHistory", "GoldPrice", "GoldPriceHistory", "Plan"})
DENIED_MODELS = frozenset({
    "AppSettings", "AuthToken", "AuthAuditLog", "PagePermission", "Role", "RolePermission", "UserRole", "UserProfile",
    "EmailTemplate", "DocumentationExecution", "Document", "LegalVersion", "PlanPrice",
})
DENIED_PREFIXES = ("AI",)          # chat history, prompts, knowledge, model versions, benchmark reports
PREFERRED_HOPS = ("owner", "asset", "company", "scenario", "category", "certificate", "rule", "from_balance", "deposit_balance")
SENSITIVE_FIELD = re.compile(r"(password|secret|token|api_?key|credential|hash|encrypt|private|hmac|signature)", re.I)
MAX_DEPTH = 3


@dataclass(frozen=True)
class ModelInfo:
    model: type
    scope: str | None            # lookup path to the owner, e.g. "owner" or "company__owner"; None = global reference data

    @property
    def name(self) -> str:
        return self.model.__name__


def _direct(model) -> bool:
    return any(f.name == "owner" and f.is_relation for f in model._meta.concrete_fields)


def _links(model):
    return [f for f in model._meta.concrete_fields if f.is_relation and (f.many_to_one or f.one_to_one)]


def _scope_path(model, core: set) -> str | None:
    frontier, seen = [(model, [])], {model}
    for _ in range(MAX_DEPTH):
        found, nxt = [], []
        for mod, path in frontier:
            for f in _links(mod):
                target = f.related_model
                if target not in core or target in seen:
                    continue
                step = path + [f.name]
                if _direct(target):
                    found.append(step)
                else:
                    nxt.append((target, step))
        if found:
            found.sort(key=lambda p: (PREFERRED_HOPS.index(p[0]) if p[0] in PREFERRED_HOPS else 99, p))
            return "__".join(found[0] + ["owner"])
        seen.update(t for t, _ in nxt)
        frontier = nxt
    return None


@lru_cache(maxsize=1)
def catalog() -> dict:
    """{ModelName: ModelInfo} for every queryable model."""
    core = set(apps.get_app_config("core").get_models())
    out = {}
    for model in sorted(core, key=lambda m: m.__name__):
        name = model.__name__
        if name in DENIED_MODELS or name.startswith(DENIED_PREFIXES) or model._meta.abstract:
            continue
        if _direct(model):
            out[name] = ModelInfo(model, "owner")
        elif name in GLOBAL_MODELS:
            out[name] = ModelInfo(model, None)
        else:
            path = _scope_path(model, core)
            if path:
                out[name] = ModelInfo(model, path)
    return out


def resolve_model(name: str) -> ModelInfo | None:
    """Case-insensitive; accepts snake_case, plurals and verbose names ('expenses', 'fixed asset')."""
    wanted = re.sub(r"[\s_\-]+", "", str(name or "")).lower()
    for info in catalog().values():
        meta = info.model._meta
        keys = {info.name.lower(), str(meta.verbose_name).replace(" ", "").lower(),
                str(meta.verbose_name_plural).replace(" ", "").lower(), info.name.lower() + "s"}
        if wanted in keys:
            return info
    return None


def scoped_queryset(info: ModelInfo, user):
    """The only way data tools read rows: every query starts from the current user's own rows."""
    manager = info.model._default_manager
    if info.scope is None:
        return manager.all()
    return manager.filter(**{info.scope: user})


def field_ok(field) -> bool:
    return not SENSITIVE_FIELD.search(field.name) and not SENSITIVE_FIELD.search(getattr(field, "attname", ""))


def visible_fields(model) -> list:
    return [f for f in model._meta.concrete_fields if field_ok(f) and f.name != "owner"]


def user_model_label() -> str:
    return settings.AUTH_USER_MODEL
