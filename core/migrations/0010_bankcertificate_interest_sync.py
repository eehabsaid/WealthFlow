from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_expense_bank"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankcertificate",
            name="last_interest_posted_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="BankCertificateInterestHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("posting_date", models.DateField()),
                ("posting_period", models.CharField(max_length=50)),
                ("interest_amount", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bank", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.bank")),
                ("certificate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interest_history", to="core.bankcertificate")),
                ("currency", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.currency")),
            ],
            options={
                "ordering": ["posting_date", "id"],
                "unique_together": {("certificate", "posting_date")},
            },
        ),
    ]
