from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_aiconversation_is_pinned"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetrenovation",
            name="furniture",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="renovations",
                to="core.assetfurniture",
            ),
        ),
        migrations.AddField(
            model_name="assetrenovation",
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
            model_name="assetrenovation",
            name="bank",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="asset_renovations",
                to="core.bank",
            ),
        ),
    ]
