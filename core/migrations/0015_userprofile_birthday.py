from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_emailtemplate_alter_bankcertificate_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="birthday",
            field=models.DateField(blank=True, null=True),
        ),
    ]
