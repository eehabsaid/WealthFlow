"""
DocumentService: composes the validation and CRUD mixins into the single
service-layer class used by fixed-asset/certificate/bank document views.
"""

from __future__ import annotations

from core.services.shared.document_service.validation_mixin import DocumentValidationMixin
from core.services.shared.document_service.crud_mixin import DocumentCrudMixin


class DocumentService(DocumentValidationMixin, DocumentCrudMixin):
    pass
