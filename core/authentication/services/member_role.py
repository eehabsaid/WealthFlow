"""Default "Member" role: created on demand and granted to newly verified users."""

from core.constants.roles import MEMBER_ROLE_DESCRIPTION, MEMBER_ROLE_KEYS, MEMBER_ROLE_NAME


def ensure_member_role(role_model, permission_model):
    """Return the Member role, creating it with its default keys if missing.

    Model classes are injected so data migrations can pass historical models.
    An existing role is returned untouched so admin edits to its keys survive.
    """
    role, created = role_model.objects.get_or_create(
        name=MEMBER_ROLE_NAME, defaults={"description": MEMBER_ROLE_DESCRIPTION}
    )
    if created:
        permission_model.objects.bulk_create(
            [permission_model(role=role, key=key) for key in MEMBER_ROLE_KEYS]
        )
    return role


def assign_member_role(user):
    """Grant the Member role to a user (idempotent)."""
    from core.models import Role, RolePermission, UserRole

    role = ensure_member_role(Role, RolePermission)
    UserRole.objects.get_or_create(user=user, role=role)
