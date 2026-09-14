import django.db.models.deletion
from django.db import migrations, models


def migrate_data_forward(apps, schema_editor):
    """Only ever reuses Currency rows that already exist (by code) — never
    auto-creates a currency. If EGP/USD aren't configured yet, those two
    placeholder prices are simply dropped; the admin adds real prices from
    Settings > Billing Plans once Settings > Currency has entries."""
    Plan = apps.get_model("core", "Plan")
    PlanPrice = apps.get_model("core", "PlanPrice")
    Invoice = apps.get_model("core", "Invoice")
    Currency = apps.get_model("core", "Currency")

    for plan in Plan.objects.all():
        for field, code in (("price_egp", "EGP"), ("price_usd", "USD")):
            amount = getattr(plan, field, None)
            if amount is None:
                continue
            currency = Currency.objects.filter(code=code).first()
            if currency is None:
                continue
            PlanPrice.objects.get_or_create(plan=plan, currency=currency, defaults={"amount": amount})

    for invoice in Invoice.objects.all():
        raw_code = (getattr(invoice, "currency", None) or "").strip().upper()
        currency = Currency.objects.filter(code=raw_code).first() or Currency.objects.order_by("order", "code").first()
        if currency is None:
            continue  # no currencies configured at all — nothing sane to link to
        invoice.currency_fk = currency
        invoice.save(update_fields=["currency_fk"])


def migrate_data_backward(apps, schema_editor):
    Invoice = apps.get_model("core", "Invoice")
    for invoice in Invoice.objects.all():
        if invoice.currency_fk_id:
            invoice.currency = invoice.currency_fk.code
            invoice.save(update_fields=["currency"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_seed_billing_plans"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="plan_prices", to="core.currency")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prices", to="core.plan")),
            ],
            options={
                "ordering": ["currency__order", "currency__code"],
                "unique_together": {("plan", "currency")},
            },
        ),
        migrations.AddField(
            model_name="invoice",
            name="currency_fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="invoices_new",
                to="core.currency",
            ),
        ),
        migrations.RunPython(migrate_data_forward, migrate_data_backward),
        migrations.RemoveField(model_name="invoice", name="currency"),
        migrations.RenameField(model_name="invoice", old_name="currency_fk", new_name="currency"),
        migrations.AlterField(
            model_name="invoice",
            name="currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="invoices",
                to="core.currency",
            ),
        ),
        migrations.RemoveField(model_name="plan", name="price_egp"),
        migrations.RemoveField(model_name="plan", name="price_usd"),
    ]
