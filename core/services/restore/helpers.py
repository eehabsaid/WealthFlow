"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

helpers.py: low-level, field-agnostic helpers used while restoring one row —
checksum hashing, field-map introspection, and single-value type coercion.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.services.backup_serializer import (
    deserialize_binary,
    deserialize_date,
    deserialize_datetime,
    deserialize_decimal,
)


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_field_map(model_class) -> dict:
    """Return {attname: field} for all concrete fields."""
    from django.db import models as dm

    return {
        f.attname: f
        for f in model_class._meta.get_fields()
        if isinstance(f, dm.Field) and not f.many_to_many and getattr(f, "concrete", True)
    }


def coerce_field(field, raw_value: Any) -> Any:
    """Convert a raw JSON value to the correct Python type for a given field."""
    from django.db import models as dm

    if raw_value is None:
        return None

    if isinstance(field, (dm.DateTimeField,)):
        return deserialize_datetime(raw_value) if isinstance(raw_value, str) else raw_value

    if isinstance(field, (dm.DateField,)):
        return deserialize_date(raw_value) if isinstance(raw_value, str) else raw_value

    if isinstance(field, (dm.DecimalField,)):
        return deserialize_decimal(raw_value)

    if isinstance(field, (dm.BinaryField,)):
        return deserialize_binary(raw_value) if isinstance(raw_value, str) else raw_value

    return raw_value
