from django.db import migrations


def _match_by_code(cache, Currency, owner_id, code):
    if not code:
        return None
    key = (owner_id, code)
    if key not in cache:
        cache[key] = Currency.objects.filter(owner_id=owner_id, code=code).first()
    return cache[key]


def repoint_currency_fks(apps, schema_editor):
    """0013/0014 cloned Currency into a per-user copy for every existing
    user, but left every EXISTING record's currency_id FK pointing at the
    original (now owner=NULL template) row. Since the create/edit forms
    populate their dropdown from the user's OWN cloned rows (different
    PKs), any code that matches "this record's currency" against "the
    user's currency list" by id started failing for all pre-migration
    data — the real cause of the create/verify failures seen in E2E.

    This repoints every affected FK, per record, to the matching
    (owner=<that record's owner>, code=<old currency's code>) row."""
    Currency = apps.get_model("core", "Currency")
    cache = {}

    def repoint(Model, currency_field, owner_id_getter, filter_kwargs=None):
        qs = Model.objects.filter(**(filter_kwargs or {}))
        qs = qs.filter(**{f"{currency_field}__owner__isnull": True}).exclude(
            **{f"{currency_field}__isnull": True}
        )
        for obj in qs.select_related(currency_field):
            owner_id = owner_id_getter(obj)
            if not owner_id:
                continue
            old_currency = getattr(obj, currency_field)
            new_currency = _match_by_code(cache, Currency, owner_id, old_currency.code)
            if new_currency and new_currency.id != old_currency.id:
                setattr(obj, f"{currency_field}_id", new_currency.id)
                obj.save(update_fields=[f"{currency_field}_id"])

    BalanceEntry = apps.get_model("core", "BalanceEntry")
    repoint(BalanceEntry, "currency", lambda o: o.owner_id)

    BalanceTransfer = apps.get_model("core", "BalanceTransfer")
    repoint(BalanceTransfer, "currency", lambda o: o.owner_id)

    BankInterest = apps.get_model("core", "BankInterest")
    repoint(BankInterest, "currency", lambda o: o.owner_id)

    BankCertificate = apps.get_model("core", "BankCertificate")
    repoint(BankCertificate, "currency", lambda o: o.owner_id)

    BankCertificateInterestHistory = apps.get_model("core", "BankCertificateInterestHistory")
    repoint(
        BankCertificateInterestHistory,
        "currency",
        lambda o: o.certificate.owner_id if o.certificate_id else None,
    )

    Expense = apps.get_model("core", "Expense")
    repoint(Expense, "currency", lambda o: o.owner_id)

    AssetPurchasePayment = apps.get_model("core", "AssetPurchasePayment")
    repoint(
        AssetPurchasePayment,
        "currency",
        lambda o: o.asset.owner_id if o.asset_id else None,
    )

    AssetSale = apps.get_model("core", "AssetSale")
    repoint(
        AssetSale,
        "deposit_currency",
        lambda o: o.asset.owner_id if o.asset_id else None,
    )

    Goal = apps.get_model("core", "Goal")
    repoint(Goal, "currency", lambda o: o.owner_id)

    PerDiem = apps.get_model("core", "PerDiem")
    repoint(
        PerDiem,
        "currency",
        lambda o: o.company.owner_id if o.company_id else None,
    )

    CurrencyExchange = apps.get_model("core", "CurrencyExchange")
    repoint(CurrencyExchange, "from_currency", lambda o: o.user_id)
    repoint(CurrencyExchange, "to_currency", lambda o: o.user_id)

    Company = apps.get_model("core", "Company")
    repoint(Company, "current_salary_currency", lambda o: o.owner_id)
    repoint(Company, "per_diem_currency", lambda o: o.owner_id)

    # Billing (Invoice, PlanPrice, UpgradeRequest) is deliberately NOT
    # repointed here — that currency must stay pinned to the platform
    # template (owner=None); see core/views/billing_views.py.


def noop_reverse(apps, schema_editor):
    """Not reversible — the original FK targets (the template rows) are
    still intact and unaffected, but recomputing which record used to
    point at exactly which one isn't tracked, and there's nothing unsafe
    about leaving records pointed at their own per-user currency."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_seed_per_user_catalogs'),
    ]

    operations = [
        migrations.RunPython(repoint_currency_fks, noop_reverse),
    ]
