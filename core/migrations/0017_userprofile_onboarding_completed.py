from django.db import migrations, models


def mark_existing_users_done(apps, schema_editor):
    """Existing accounts never see the first-run wizard."""
    apps.get_model("core", "UserProfile").objects.update(onboarding_completed=True)


class Migration(migrations.Migration):
    dependencies = [("core", "0016_remove_admin_approval_step")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_users_done, migrations.RunPython.noop),
    ]
