"""
backup_serializer package
===========================
Split from the former `backup_serializer.py` module (200-line refactor).
Core serialisation / deserialisation helpers for the WealthFlow backup &
restore system.

Sibling files:
- value_conversion.py  serialize_value + deserialize_date/datetime/decimal/binary.
- content_type.py       resolve_content_type + content_type_label.
- export_order.py       get_model_export_order() — the ordered table list
                        used by both backup and restore.
- signal_management.py  disconnect_restore_signals/reconnect_signals (used to
                        suspend balance-sync signals during bulk restore) and
                        run_post_restore_sync (post-restore sync routines).

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.services.backup_serializer.content_type import content_type_label, resolve_content_type
from core.services.backup_serializer.export_order import get_model_export_order
from core.services.backup_serializer.signal_management import (
    disconnect_restore_signals,
    reconnect_signals,
    run_post_restore_sync,
)
from core.services.backup_serializer.value_conversion import (
    deserialize_binary,
    deserialize_date,
    deserialize_datetime,
    deserialize_decimal,
    serialize_value,
)

__all__ = [
    "serialize_value",
    "deserialize_date",
    "deserialize_datetime",
    "deserialize_decimal",
    "deserialize_binary",
    "resolve_content_type",
    "content_type_label",
    "get_model_export_order",
    "disconnect_restore_signals",
    "reconnect_signals",
    "run_post_restore_sync",
]
