from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_balanceentry_purity_goldsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="bank",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="expenses",
                to="core.bank",
            ),
        ),
    ]
