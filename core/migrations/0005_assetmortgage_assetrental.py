# Generated manually for fixed assets mortgage and rental support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_assetphoto_filename_assetphoto_image_data_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetMortgage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("loan_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("remaining_balance", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("monthly_installment", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("interest_rate", models.DecimalField(decimal_places=4, default=0, max_digits=8)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="mortgage", to="core.fixedasset"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AssetRental",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monthly_rent", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("occupancy_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("tenant_name", models.CharField(blank=True, max_length=200)),
                ("contract_start", models.DateField(blank=True, null=True)),
                ("contract_end", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="rental", to="core.fixedasset"),
                ),
            ],
        ),
    ]
