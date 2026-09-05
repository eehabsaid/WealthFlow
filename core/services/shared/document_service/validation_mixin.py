"""
Private helpers for resolving parent models/instances, extracting and
validating uploaded files, and validating document categories.
"""

from __future__ import annotations

import hashlib
import os

from django.core.exceptions import ValidationError

from core.models import AppSettings

from core.services.shared.document_service.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    DOCUMENT_CATEGORIES,
    PARENT_MODEL_MAP,
    FilePayload,
)


class DocumentValidationMixin:
    def _max_upload_size(self) -> int:
        setting = AppSettings.get("documents_max_upload_mb", "10")
        try:
            mb = float(setting)
        except (TypeError, ValueError):
            mb = 10
        if mb <= 0:
            mb = 10
        return int(mb * 1024 * 1024)

    def _get_parent_model(self, parent_type: str):
        key = str(parent_type or "").strip().lower()
        model = PARENT_MODEL_MAP.get(key)
        if not model:
            raise ValidationError("invalid_parent_type")
        return key, model

    def _get_parent_instance(self, parent_type: str, parent_id: int):
        normalized_type, model = self._get_parent_model(parent_type)
        parent = model.objects.filter(pk=parent_id).first()
        if parent is None:
            raise ValidationError("parent_not_found")
        return normalized_type, parent

    def _extract_file(self, uploaded_file) -> FilePayload:
        if uploaded_file is None:
            raise ValidationError("file_required")

        name = str(getattr(uploaded_file, "name", "") or "").strip()
        mime_type = str(getattr(uploaded_file, "content_type", "") or "").strip().lower()
        size = int(getattr(uploaded_file, "size", 0) or 0)

        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError("invalid_file_type")

        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError("invalid_file_type")

        max_size = self._max_upload_size()
        if size <= 0 or size > max_size:
            raise ValidationError("file_too_large")

        content = uploaded_file.read()
        if len(content) != size:
            size = len(content)
        if size <= 0 or size > max_size:
            raise ValidationError("file_too_large")

        return FilePayload(name=name, mime_type=mime_type or self._mime_from_extension(ext), size=size, content=content)

    def _mime_from_extension(self, ext: str) -> str:
        mapping = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        return mapping.get(ext.lower(), "application/octet-stream")

    def _validate_category(self, parent_type: str, category: str):
        category_text = str(category or "").strip()
        if not category_text:
            raise ValidationError("document_category_required")

        allowed = DOCUMENT_CATEGORIES.get(parent_type)
        if allowed and category_text not in allowed:
            raise ValidationError("invalid_document_category")

        return category_text

    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
