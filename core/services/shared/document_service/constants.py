"""
Static allow-lists, upload size default, parent-model map, per-parent
document categories, and the FilePayload carrier used across the
Document Service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Type

from core.models import AssetInsurance, Bank, BankCertificate, FixedAsset

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
