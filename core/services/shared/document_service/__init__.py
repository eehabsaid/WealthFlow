"""Umbrella re-export for the shared Document Service, so both
core/services/shared/__init__.py and any other file can keep doing
`from core.services.shared.document_service import DocumentService`
unchanged, without needing to know this moved from a flat
core/services/shared/document_service.py into this package.

ORGANIZING PRINCIPLE: mixin composition by concern for the single
DocumentService class — private validation/extraction helpers vs. the
public CRUD surface used by views.

STRUCTURE / CONVENTION:
  - constants.py          ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES,
                           DEFAULT_MAX_UPLOAD_BYTES, PARENT_MODEL_MAP,
                           DOCUMENT_CATEGORIES, FilePayload dataclass.
  - validation_mixin.py   DocumentValidationMixin — private helpers:
                           _max_upload_size, _get_parent_model,
                           _get_parent_instance, _extract_file,
                           _mime_from_extension, _validate_category,
                           _hash_content.
  - crud_mixin.py         DocumentCrudMixin — list_documents,
                           upload_document, get_document,
                           replace_document, delete_document,
                           get_document_content, categories_for_parent.
  - service.py            DocumentService — composes the two mixins.
  - If any file here grows past ~200 lines, split it by concern into
    more files in this same folder.
  - Always update this __init__.py's imports/__all__ to match.
"""

from core.services.shared.document_service.service import DocumentService

__all__ = ["DocumentService"]
