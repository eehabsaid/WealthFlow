from datetime import date

from django.db import migrations


def seed_goal_mock_data(apps, schema_editor):
    Goal = apps.get_model("core", "Goal")
    Currency = apps.get_model("core", "Currency")

    if Goal.objects.exists():
        return

    egp = Currency.objects.filter(code__iexact="EGP").order_by("id").first()
    if egp is None:
        return

    mock_goals = [
        {
            "name": "Emergency Fund",
            "goal_type": "Safety",
            "target_amount": 120000,
            "current_saved_amount": 45000,
            "target_date": date(2027, 1, 31),
            "priority": "High",
            "notes": "Build a 6-month emergency buffer.",
        },
        {
            "name": "Home Down Payment",
            "goal_type": "Property",
            "target_amount": 600000,
            "current_saved_amount": 210000,
            "target_date": date(2028, 6, 30),
            "priority": "High",
            "notes": "Primary residence down payment plan.",
        },
        {
            "name": "Family Car Upgrade",
            "goal_type": "Vehicle",
            "target_amount": 350000,
            "current_saved_amount": 140000,
            "target_date": date(2027, 9, 30),
            "priority": "Medium",
            "notes": "Upgrade to a lower-maintenance family vehicle.",
        },
        {
            "name": "Education Fund",
            "goal_type": "Education",
            "target_amount": 250000,
            "current_saved_amount": 90000,
            "target_date": date(2028, 3, 31),
            "priority": "Medium",
            "notes": "Annual school and certification reserve.",
        },
        {
            "name": "Annual Travel Plan",
            "goal_type": "Lifestyle",
            "target_amount": 100000,
            "current_saved_amount": 30000,
            "target_date": date(2027, 8, 15),
            "priority": "Low",
            "notes": "Family vacation and travel-related expenses.",
        },
        {
            "name": "Business Expansion Reserve",
            "goal_type": "Business",
            "target_amount": 500000,
            "current_saved_amount": 175000,
            "target_date": date(2028, 12, 31),
            "priority": "High",
            "notes": "Capital reserve for business growth opportunities.",
        },
    ]

    Goal.objects.bulk_create(
        [
            Goal(
                name=item["name"],
                goal_type=item["goal_type"],
                target_amount=item["target_amount"],
                current_saved_amount=item["current_saved_amount"],
                target_date=item["target_date"],
                priority=item["priority"],
                notes=item["notes"],
                currency_id=egp.id,
            )
            for item in mock_goals
        ]
    )


def unseed_goal_mock_data(apps, schema_editor):
    Goal = apps.get_model("core", "Goal")
    mock_names = [
        "Emergency Fund",
        "Home Down Payment",
        "Family Car Upgrade",
        "Education Fund",
        "Annual Travel Plan",
        "Business Expansion Reserve",
    ]
    Goal.objects.filter(name__in=mock_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_goal"),
    ]

    operations = [
        migrations.RunPython(seed_goal_mock_data, unseed_goal_mock_data),
    ]
