"""
Public CRUD operations for uploading, listing, retrieving, replacing,
and deleting parent-linked documents.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from core.models import Document

from core.services.shared.document_service.constants import DOCUMENT_CATEGORIES


class DocumentCrudMixin:
    def list_documents(self, parent_type: str, parent_id: int) -> List[dict]:
        normalized_type, parent = self._get_parent_instance(parent_type, parent_id)
        ct = ContentType.objects.get_for_model(parent.__class__)
        docs = Document.objects.filter(
            parent_object_type=normalized_type,
            content_type=ct,
            object_id=parent.id,
        ).order_by("-upload_date", "-id")
        return [d.to_dict() for d in docs]

    def upload_document(self, parent_type: str, parent_id: int, uploaded_file, uploaded_by=None, category: str = "", notes: str = "") -> dict:
        normalized_type, parent = self._get_parent_instance(parent_type, parent_id)
        payload = self._extract_file(uploaded_file)
        category_value = self._validate_category(normalized_type, category)
        file_hash = self._hash_content(payload.content)

        ct = ContentType.objects.get_for_model(parent.__class__)
        duplicate = Document.objects.filter(
            parent_object_type=normalized_type,
            content_type=ct,
            object_id=parent.id,
            file_hash=file_hash,
            original_file_name=payload.name,
            file_size=payload.size,
        ).exists()
        if duplicate:
            raise ValidationError("duplicate_document")

        doc = Document.objects.create(
            parent_object_type=normalized_type,
            content_type=ct,
            object_id=parent.id,
            document_category=category_value,
            original_file_name=payload.name,
            mime_type=payload.mime_type,
            file_size=payload.size,
            file_content=payload.content,
            file_hash=file_hash,
            uploaded_by=uploaded_by if getattr(uploaded_by, "is_authenticated", False) else None,
            notes=str(notes or "").strip(),
        )
        return doc.to_dict()

    def get_document(self, document_id: int) -> Optional[Document]:
        return Document.objects.filter(pk=document_id).first()

    def replace_document(self, document_id: int, uploaded_file, uploaded_by=None, category: Optional[str] = None, notes: Optional[str] = None) -> dict:
        doc = self.get_document(document_id)
        if doc is None:
            raise ValidationError("document_not_found")

        payload = self._extract_file(uploaded_file)
        category_value = doc.document_category if category is None else self._validate_category(doc.parent_object_type, category)
        file_hash = self._hash_content(payload.content)

        duplicate = Document.objects.filter(
            parent_object_type=doc.parent_object_type,
            content_type=doc.content_type,
            object_id=doc.object_id,
            file_hash=file_hash,
            original_file_name=payload.name,
            file_size=payload.size,
        ).exclude(pk=doc.id).exists()
        if duplicate:
            raise ValidationError("duplicate_document")

        doc.document_category = category_value
        doc.original_file_name = payload.name
        doc.mime_type = payload.mime_type
        doc.file_size = payload.size
        doc.file_content = payload.content
        doc.file_hash = file_hash
        if notes is not None:
            doc.notes = str(notes or "").strip()
        if getattr(uploaded_by, "is_authenticated", False):
            doc.uploaded_by = uploaded_by
        doc.save()
        return doc.to_dict()

    def delete_document(self, document_id: int) -> bool:
        doc = self.get_document(document_id)
        if doc is None:
            return False
        doc.delete()
        return True

    def get_document_content(self, document_id: int) -> Tuple[Optional[dict], Optional[bytes]]:
        doc = self.get_document(document_id)
        if doc is None:
            return None, None
        return doc.to_dict(), bytes(doc.file_content or b"")

    def categories_for_parent(self, parent_type: str) -> List[str]:
        normalized_type, _ = self._get_parent_model(parent_type)
        return DOCUMENT_CATEGORIES.get(normalized_type, ["Related Files"])
