from django.db import models
from django.conf import settings

from core.constants import PAGE_PERMISSION_CHOICES
from core.constants.roles import grantable_permission_choices

__all__ = [
    "PagePermission",
    "PAGE_PERMISSION_CHOICES",
    "Role",
    "RolePermission",
    "UserRole",
]


class PagePermission(models.Model):
    """A per-user override on top of whatever the user's Role(s) grant.

    `granted=True` (the historical default — see the migration backfill)
    grants the key even if no role does; `granted=False` revokes it even
    if a role grants it. Overrides always win over role grants — see
    core.authentication.utils.auth_utils.effective_permission_keys().

    Despite the name, `page` now holds any key from the unified
    permission-key namespace (main-app pages AND settings tabs), not just
    main-app pages — kept for backward compatibility with existing rows,
    imports, and the `page_permissions` related_name used across the app.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="page_permissions",
    )
    page = models.CharField(max_length=50, choices=grantable_permission_choices)
    granted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "page"]
        ordering = ["user__username", "page"]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "page": self.page,
            "granted": self.granted,
        }

    def __str__(self):
        verb = "granted" if self.granted else "revoked"
        return f"{self.user.username} → {self.page} ({verb})"


class Role(models.Model):
    """A named, admin-defined bundle of grantable permission keys. Assigned
    to users via UserRole (many-to-many — a user may hold several roles;
    effective access is the union of all their roles' grants)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def to_dict(self, include_keys=True):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }
        if include_keys:
            data["keys"] = list(self.permissions.values_list("key", flat=True))
        return data

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    key = models.CharField(max_length=50, choices=grantable_permission_choices)

    class Meta:
        unique_together = ["role", "key"]
        ordering = ["role__name", "key"]

    def __str__(self):
        return f"{self.role.name} → {self.key}"


class UserRole(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "role"]
        ordering = ["user__username", "role__name"]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role.name,
        }

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"
