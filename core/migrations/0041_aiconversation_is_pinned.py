from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_seed_prompt_categories_and_prompts"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiconversation",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
    ]
