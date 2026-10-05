from django.db import migrations

from core.constants.roles import MEMBER_ROLE_NAME

NEW_KEYS = ["settings_myai"]


def grant_new_keys_to_member_role(apps, schema_editor):
    """ensure_member_role() leaves an existing Member role untouched, so deployments that already have it
    never receive keys added to MEMBER_ROLE_KEYS later. Additive only."""
    Role = apps.get_model("core", "Role")
    RolePermission = apps.get_model("core", "RolePermission")
    role = Role.objects.filter(name=MEMBER_ROLE_NAME).first()
    if role is None:
        return
    for key in NEW_KEYS:
        RolePermission.objects.get_or_create(role=role, key=key)


def revoke_new_keys_from_member_role(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    RolePermission = apps.get_model("core", "RolePermission")
    role = Role.objects.filter(name=MEMBER_ROLE_NAME).first()
    if role is None:
        return
    RolePermission.objects.filter(role=role, key__in=NEW_KEYS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_userprofile_terms_consent"),
    ]

    operations = [
        migrations.RunPython(grant_new_keys_to_member_role, revoke_new_keys_from_member_role),
    ]
