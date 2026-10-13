"""Registry of downloadable answer formats. Adding a format = one `register(ExportFormat(...))` call in
exports/builders/: detection words, link label, file extension and MIME type all live on the entry, so no
other module lists formats. `builder(document, lang) -> bytes` turns an ExportDocument into the file."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable

from .document import ExportDocument

Builder = Callable[[ExportDocument, str], bytes]


@dataclass(frozen=True)
class ExportFormat:
    key: str                       # URL / registry key, e.g. "xlsx"
    label: str                     # shown in the link text, e.g. "Excel (.xlsx)"
    extension: str                 # file extension without the dot
    mime: str
    builder: Builder
    terms: tuple[str, ...]         # regexes on normalised text (en / ar / fr / de) that name this format
    weak_terms: tuple[str, ...] = ()   # ambiguous words ("word"): count only next to another file request ("pdf and word")
    offer_by_default: bool = True  # offered when the user only says "export" / "download" without a format
    order: int = 100               # position among the offered links


_FORMATS: dict[str, ExportFormat] = {}


def register(fmt: ExportFormat) -> ExportFormat:
    _FORMATS[fmt.key] = fmt
    return fmt


def get_format(key: str) -> ExportFormat | None:
    _load()
    return _FORMATS.get(str(key or "").strip().lower())


def all_formats() -> list[ExportFormat]:
    _load()
    return sorted(_FORMATS.values(), key=lambda f: (f.order, f.key))


def default_formats() -> list[ExportFormat]:
    return [f for f in all_formats() if f.offer_by_default]


def _load() -> None:
    if not _FORMATS:
        import_module(".builders", __package__)   # importing the package registers every builtin format
