from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_userprofile_birthday"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetPurchasePayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "payment_method",
                    models.CharField(
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
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchase_payments", to="core.fixedasset"),
                ),
                (
                    "bank",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_purchase_payments", to="core.bank"),
                ),
                (
                    "currency",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_purchase_payments", to="core.currency"),
                ),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddField(
            model_name="assetsale",
            name="deposit_bank",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_sales_deposits", to="core.bank"),
        ),
        migrations.AddField(
            model_name="assetsale",
            name="deposit_currency",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_sales_deposits", to="core.currency"),
        ),
        migrations.AddField(
            model_name="assetsale",
            name="deposit_method",
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
    ]
