from django.db import migrations


def pin_existing_users(apps, schema_editor):
    """Save today's platform default on every user who never chose one, so a
    later change of the platform default cannot move existing users."""
    AppSettings = apps.get_model("core", "AppSettings")
    UserProfile = apps.get_model("core", "UserProfile")
    row = AppSettings.objects.filter(key="home_currency", owner__isnull=True).first()
    code = str(row.value if row and row.value else "EGP").strip().upper() or "EGP"
    UserProfile.objects.filter(preferred_currency="").update(preferred_currency=code)


class Migration(migrations.Migration):
    dependencies = [("core", "0018_userprofile_preferred_currency")]
    operations = [migrations.RunPython(pin_existing_users, migrations.RunPython.noop)]
