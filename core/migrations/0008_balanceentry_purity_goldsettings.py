from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_golddetails_cashback_per_gram"),
    ]

    operations = [
        migrations.AddField(
            model_name="balanceentry",
            name="purity",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.CreateModel(
            name="GoldPuritySetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=20, unique=True)),
                ("label", models.CharField(max_length=50)),
                ("cashback_per_gram", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["order", "key"]},
        ),
        migrations.CreateModel(
            name="GoldTypeSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["order", "name"]},
        ),
    ]
