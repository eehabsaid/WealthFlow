from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_fixedasset_asset_type_assetinsurance_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="golddetails",
            name="cashback_per_gram",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12),
        ),
    ]
