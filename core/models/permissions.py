from django.db import models
from django.conf import settings

from core.constants import PAGE_PERMISSION_CHOICES

class PagePermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="page_permissions",
    )
    page = models.CharField(max_length=50, choices=PAGE_PERMISSION_CHOICES)
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
        }

    def __str__(self):
        return f"{self.user.username} → {self.get_page_display()}"
