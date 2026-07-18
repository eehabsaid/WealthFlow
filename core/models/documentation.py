from django.db import models
from django.contrib.auth.models import User

class DocumentationExecutionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"

class DocumentationExecutionType(models.TextChoices):
    CAPTURE = "CAPTURE", "Capture"
    GENERATION = "GENERATION", "Generation"
    BOTH = "BOTH", "Capture & Generate"

class DocumentationExecution(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    execution_type = models.CharField(
        max_length=20,
        choices=DocumentationExecutionType.choices,
        default=DocumentationExecutionType.BOTH
    )
    language = models.CharField(max_length=50)
    theme = models.CharField(max_length=50)
    device_category = models.CharField(max_length=50)
    device_type = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=DocumentationExecutionStatus.choices,
        default=DocumentationExecutionStatus.PENDING
    )
    screenshots_count = models.IntegerField(default=0)
    failed_pages = models.IntegerField(default=0)
    pages = models.IntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    missing_content_count = models.IntegerField(default=0)
    files_generated = models.JSONField(default=list, blank=True)
    git_commit_hash = models.CharField(max_length=40, blank=True, null=True)
    app_version = models.CharField(max_length=20, blank=True, null=True)
    engine_version = models.CharField(max_length=20, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Doc Execution {self.id} - {self.status}"
