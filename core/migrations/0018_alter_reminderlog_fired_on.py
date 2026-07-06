from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_alter_pagepermission_page"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reminderlog",
            name="fired_on",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
    ]
