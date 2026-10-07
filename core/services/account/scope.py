"""Which rows belong to one user, for every table in the backup export order.

One rule set drives both "export my data" and "delete my account", so they can never disagree:
  * owned   - reached through an owner/user FK, directly or via a parent (asset__owner, rule__owner...).
  * special - owned but not reachable by FK alone (Document via GenericFK, CurrencyExchange via balances,
              django-axes rows keyed by username).
  * global  - shared platform tables (plans, rates, roles, knowledge...). Never exported or deleted.
core/tests/account/test_scope_coverage.py fails when a new model in get_model_export_order() is none of these.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

OWNER_FIELD_NAMES = ("owner", "user")

GLOBAL_MODELS = {
    "ContentType", "Group", "Permission", "Group_permissions", "EmailTemplate", "LegalVersion",
    "ExchangeRate", "GoldPrice", "GoldPriceHistory", "ExchangeRateHistory", "AIKnowledgeEntry",
    "AIModelVersion", "AIBenchmarkReport", "AIPromptCategory", "DocumentationExecution",
    "Plan", "PlanPrice", "Role", "RolePermission",
}
# Login secrets: never put in a downloadable file.
EXCLUDED_SECRET_MODELS = {"AuthToken"}
SECRET_FIELDS = {"User": {"password"}}
AXES_MODELS = {"AccessAttempt", "AccessAttemptExpiration", "AccessFailureLog", "AccessLog"}
SPECIAL_MODELS = {"User", "Document", "CurrencyExchange"} | AXES_MODELS


def _owner_path(model, depth=0, seen=()):
    if depth > 3 or model in seen:
        return None
    for name in OWNER_FIELD_NAMES:
        try:
            f = model._meta.get_field(name)
        except Exception:
            continue
        if isinstance(f, (models.ForeignKey, models.OneToOneField)) and f.related_model is User:
            return name
    for f in model._meta.concrete_fields:
        if isinstance(f, (models.ForeignKey, models.OneToOneField)) and f.related_model not in (User, model):
            sub = _owner_path(f.related_model, depth + 1, seen + (model,))
            if sub:
                return f"{f.name}__{sub}"
    return None


def classify(model) -> str:
    name = model.__name__
    if name in GLOBAL_MODELS or name in EXCLUDED_SECRET_MODELS:
        return "global"
    if name in SPECIAL_MODELS:
        return "special"
    return "owned" if _owner_path(model) else "unclassified"


def _document_q(user):
    from django.contrib.contenttypes.models import ContentType

    from core.models import FixedAsset

    ct = ContentType.objects.get_for_model(FixedAsset)
    ids = FixedAsset.objects.filter(owner=user).values("id")
    return Q(content_type=ct, object_id__in=ids) | Q(uploaded_by=user)


def owned_queryset(model, user):
    """Rows of `model` that belong to `user` (empty queryset for global tables)."""
    kind, name = classify(model), model.__name__
    if kind == "owned":
        return model.objects.filter(**{_owner_path(model): user})
    if name == "User":
        return model.objects.filter(pk=user.pk)
    if name == "Document":
        return model.objects.filter(_document_q(user))
    if name == "CurrencyExchange":
        return model.objects.filter(Q(user=user) | Q(from_balance__owner=user) | Q(to_balance__owner=user))
    if name in AXES_MODELS:
        return _axes_queryset(model, user)
    return model.objects.none()


def _axes_queryset(model, user):
    if name_has_field(model, "username"):
        return model.objects.filter(username=user.username)
    if name_has_field(model, "access_attempt"):  # AccessAttemptExpiration -> AccessAttempt
        return model.objects.filter(access_attempt__username=user.username)
    return model.objects.none()


def name_has_field(model, field):
    return any(f.name == field for f in model._meta.get_fields())
