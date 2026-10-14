"""Downloadable answers: any assistant answer (instant engine table, model prose, investigator) can be
downloaded as Excel / Word / PDF / CSV / TXT. Formats are registered in builders/; see registry.py."""

from .build import build_file, document_for
from .full_data import formats_from_tool_calls
from .followup import FOLLOWUP_TOOL, is_pure_followup, only_a_file_request, previous_answer
from .intent import detect, requested, strip_export_terms
from .links import append_links, export_url, links_line
from .notice import ExportNoticeProvider
from .registry import ExportFormat, all_formats, default_formats, get_format, register

__all__ = [
    "ExportFormat", "ExportNoticeProvider", "FOLLOWUP_TOOL", "all_formats", "append_links", "build_file", "default_formats",
    "detect", "formats_from_tool_calls", "requested", "strip_export_terms", "document_for", "export_url", "get_format", "is_pure_followup", "only_a_file_request", "links_line", "previous_answer", "register",
]
