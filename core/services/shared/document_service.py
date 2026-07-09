from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Type

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from core.models import AppSettings, AssetInsurance, Bank, BankCertificate, Document, FixedAsset


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
}
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


PARENT_MODEL_MAP: Dict[str, Type] = {
    "fixed_asset": FixedAsset,
    "bank_certificate": BankCertificate,
    "bank": Bank,
    "asset_insurance": AssetInsurance,
}


DOCUMENT_CATEGORIES: Dict[str, List[str]] = {
    "fixed_asset": [
        "Property Documents",
        "Purchase Contracts",
        "Ownership Documents",
        "Tax Documents",
        "Vehicle Licenses",
        "Registration",
        "Insurance Documents",
        "Maintenance Documents",
        "Purchase/Sale Contracts",
        "Certificate Documents",
        "Renewal Documents",
        "Bank Statements",
        "Bank Contracts",
        "Account Documents",
        "Insurance Policies",
        "Claims",
        "Warranty Documents",
        "Related Files",
        "Purchase Documents",
    ],
    "bank_certificate": [
        "Certificate Documents",
        "Renewal Documents",
        "Related Files",
    ],
    "bank": [
        "Bank Statements",
        "Bank Contracts",
        "Account Documents",
        "Related Files",
    ],
    "asset_insurance": [
        "Insurance Policies",
        "Claims",
        "Renewal Documents",
        "Related Files",
    ],
}


@dataclass
class FilePayload:
    name: str
    mime_type: str
    size: int
    content: bytes


class DocumentService:
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
