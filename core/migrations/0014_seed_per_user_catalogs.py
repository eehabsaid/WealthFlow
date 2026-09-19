from django.db import migrations


CATALOG_MODELS = ["Currency", "GoldTypeSetting", "GoldPuritySetting", "CertificateStatus"]


def clone_field_values(instance, model_fields):
    """Copy every concrete field except pk/owner into a plain dict."""
    return {
        f.name: getattr(instance, f.name)
        for f in model_fields
        if f.name not in ("id", "owner")
    }


def seed_existing_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    users = list(User.objects.all())
    if not users:
        return

    for model_name in CATALOG_MODELS:
        Model = apps.get_model("core", model_name)
        template_rows = list(Model.objects.filter(owner__isnull=True))
        if not template_rows:
            continue
        model_fields = Model._meta.fields
        to_create = []
        for user in users:
            for row in template_rows:
                values = clone_field_values(row, model_fields)
                values["owner_id"] = user.id
                to_create.append(Model(**values))
        if to_create:
            Model.objects.bulk_create(to_create, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    """Not reversible — deleting the per-user clones on rollback would
    destroy any edits users have since made to their own copies."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_per_user_catalogs'),
    ]

    operations = [
        migrations.RunPython(seed_existing_users, noop_reverse),
    ]
