from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is created, and seed
    their own copy of the per-user catalogs (Currency, GoldTypeSetting,
    GoldPuritySetting, CertificateStatus) from the platform template."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        _seed_catalogs_for_user(instance)
        from core.services.shared.base_currency import pin_user_base_currency

        pin_user_base_currency(instance)


def _seed_catalogs_for_user(user):
    from core.models import Currency, GoldTypeSetting, GoldPuritySetting, CertificateStatus
    from core.views.settings.gold.gold_settings_helpers import _seed_gold_settings_defaults
    from core.services.onboarding import seed_default_expense_categories

    _clone_or_seed(Currency, user, _DEFAULT_CURRENCIES)
    _clone_or_seed(CertificateStatus, user, _DEFAULT_CERT_STATUSES)
    # Try cloning from a template first; _seed_gold_settings_defaults is
    # idempotent (get_or_create) so calling it afterward is a safe no-op
    # if the clone already succeeded, and the real fallback if it didn't.
    _clone_or_seed(GoldTypeSetting, user, [])
    _clone_or_seed(GoldPuritySetting, user, [])
    _seed_gold_settings_defaults(user)
    seed_default_expense_categories(user)


_DEFAULT_CURRENCIES = [
    {"code": "EGP", "symbol": "ج.م", "flag": "🇪🇬", "name": "Egyptian Pound", "order": 1},
    {"code": "USD", "symbol": "$", "flag": "🇺🇸", "name": "US Dollar", "order": 2},
    {"code": "SAR", "symbol": "﷼", "flag": "🇸🇦", "name": "Saudi Riyal", "order": 3},
    # "Gold" is a pseudo-currency the gold balance sync depends on
    # (core/services/fixed_assets/gold_sync_service) — without it, a
    # user's gold assets never get a matching BalanceEntry at all.
    {"code": "Gold", "symbol": "g", "flag": "🪙", "name": "Gold (grams)", "order": 4},
]

_DEFAULT_CERT_STATUSES = [
    {"name": "Active", "color_hex": "#1a6ef5", "is_default": True, "order": 1},
    {"name": "Matured", "color_hex": "#f5a623", "is_default": False, "order": 2},
    {"name": "Closed", "color_hex": "#6c757d", "is_default": False, "is_terminal": True, "order": 3},
]


def _clone_or_seed(Model, user, fallback_defaults):
    """Clone this user's copy from the platform template (owner=NULL rows).
    If no template exists yet (a genuinely fresh install with no prior
    data), fall back to sensible hardcoded defaults instead of leaving the
    user with an empty catalog."""
    if Model.objects.filter(owner=user).exists():
        return
    template_rows = list(Model.objects.filter(owner__isnull=True))
    if template_rows:
        clones = []
        for row in template_rows:
            values = {
                f.name: getattr(row, f.name)
                for f in Model._meta.fields
                if f.name not in ("id", "owner")
            }
            values["owner"] = user
            clones.append(Model(**values))
        if clones:
            Model.objects.bulk_create(clones, ignore_conflicts=True)
    elif fallback_defaults:
        Model.objects.bulk_create(
            [Model(owner=user, **d) for d in fallback_defaults], ignore_conflicts=True
        )
