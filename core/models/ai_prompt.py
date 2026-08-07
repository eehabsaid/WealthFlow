from django.db import models
from django.contrib.auth.models import User


class AIPromptCategory(models.Model):
    """
    First-class category for AI Workspace prompts.
    """
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, default="bi-folder")
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class AIPrompt(models.Model):
    """
    Centralized reusable prompt entity for WealthFlow AI Workspace.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_prompts",
    )
    name = models.CharField(max_length=255)
    content = models.TextField()
    category = models.ForeignKey(
        AIPromptCategory,
        on_delete=models.PROTECT,
        related_name="prompts",
    )
    description = models.TextField(blank=True, default="")
    translation_key = models.CharField(max_length=100, blank=True, default="")
    is_favorite = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["-is_favorite", "display_order", "-updated_at", "name"]

    def __str__(self):
        return self.name
