from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0042_assetrenovation_furniture_payment_bank"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetacquisitioncost",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("Cash", "Cash"),
                    ("Card", "Card"),
                    ("Bank", "Bank"),
                    ("Bank Transfer", "Bank Transfer"),
                ],
                default="Cash",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="assetacquisitioncost",
            name="bank",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="asset_acquisition_costs",
                to="core.bank",
            ),
        ),
        migrations.AddField(
            model_name="assetfurniture",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("Cash", "Cash"),
                    ("Card", "Card"),
                    ("Bank", "Bank"),
                    ("Bank Transfer", "Bank Transfer"),
                ],
                default="Cash",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="assetfurniture",
            name="bank",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="asset_furniture",
                to="core.bank",
            ),
        ),
        migrations.AddField(
            model_name="assetrental",
            name="receive_method",
            field=models.CharField(
                choices=[
                    ("Cash", "Cash"),
                    ("Card", "Card"),
                    ("Bank", "Bank"),
                    ("Bank Transfer", "Bank Transfer"),
                ],
                default="Cash",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="assetrental",
            name="bank",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="asset_rentals",
                to="core.bank",
            ),
        ),
    ]
