from django.db import migrations
from django.db.models import Q


def backfill_sysadmin(apps, schema_editor):
    """Preserve access for everyone who currently relies on is_staff/is_superuser
    as their app-level admin bypass — per decision, they become sysadmin."""
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("core", "UserProfile")
    for user in User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.is_sysadmin:
            profile.is_sysadmin = True
            profile.save(update_fields=["is_sysadmin"])


def noop_reverse(apps, schema_editor):
    """Not meaningfully reversible — leaving is_sysadmin as-is on reverse
    avoids silently stripping access someone may have since granted
    through the new system directly."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_role_based_access'),
    ]

    operations = [
        migrations.RunPython(backfill_sysadmin, noop_reverse),
    ]
