from django.db import migrations


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("core", "Plan")
    Plan.objects.get_or_create(
        code="basic",
        defaults={
            "name": "Basic",
            "price_egp": 199,
            "price_usd": 5,
            "billing_interval_days": 30,
            "is_active": True,
            "sort_order": 1,
        },
    )
    Plan.objects.get_or_create(
        code="pro",
        defaults={
            "name": "Pro",
            "price_egp": 399,
            "price_usd": 10,
            "billing_interval_days": 30,
            "is_active": True,
            "sort_order": 2,
        },
    )


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("core", "Plan")
    Plan.objects.filter(code__in=["basic", "pro"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_billing_plan_subscription_invoice"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
