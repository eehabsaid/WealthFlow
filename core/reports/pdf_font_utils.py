"""Re-export: the implementation now lives in ai.services.exports.pdf_fonts (ai/ owns it so it can be copied alone)."""
from ai.services.exports.pdf_fonts import _REGISTERED_PDF_BOLD_FONT, _REGISTERED_PDF_FONT, _base_dir, get_arabic_pdf_font, has_arabic_text, is_already_reshaped, process_pdf_text  # noqa: F401

__all__ = [
    "_REGISTERED_PDF_BOLD_FONT",
    "_REGISTERED_PDF_FONT",
    "_base_dir",
    "get_arabic_pdf_font",
    "has_arabic_text",
    "is_already_reshaped",
    "process_pdf_text",
]
