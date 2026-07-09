from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class Document(models.Model):
    parent_object_type = models.CharField(max_length=100, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    parent_object = GenericForeignKey("content_type", "object_id")

    document_category = models.CharField(max_length=100)
    original_file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    file_content = models.BinaryField()
    file_hash = models.CharField(max_length=64, blank=True, db_index=True)

    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-upload_date", "-id"]
        indexes = [
            models.Index(fields=["parent_object_type", "content_type", "object_id"]),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "parent_object_type": self.parent_object_type,
            "parent_object_id": self.object_id,
            "document_category": self.document_category,
            "original_file_name": self.original_file_name,
            "mime_type": self.mime_type,
            "file_size": int(self.file_size or 0),
            "upload_date": self.upload_date.isoformat() if self.upload_date else "",
            "uploaded_by": getattr(self.uploaded_by, "username", ""),
            "notes": self.notes,
        }
