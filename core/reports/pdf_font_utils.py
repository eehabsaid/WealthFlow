"""
WealthFlow PDF & Excel Font & Text Formatting Utilities
Provides:
 1. Robust font registration across media/, static/fonts/, and system font paths.
 2. Arabic text reshaping and BiDi direction formatting for ReportLab PDF rendering.
 3. Safe cell string formatting for Excel openpyxl exports.
"""

import os
import re
import glob
from django.conf import settings

_REGISTERED_PDF_FONT = None
_REGISTERED_PDF_BOLD_FONT = None

def get_arabic_pdf_font():
    """
    Finds and registers a TTF font supporting Arabic characters in ReportLab.
    Searches in:
     - settings.MEDIA_ROOT (and media/fonts/)
     - static/fonts/ (arial.ttf, arialbd.ttf, amiri.ttf, tahoma.ttf, etc.)
     - System font directories (C:\\Windows\\Fonts\\, /usr/share/fonts/)
    Returns (font_name, font_bold_name).
    """
    global _REGISTERED_PDF_FONT, _REGISTERED_PDF_BOLD_FONT
    if _REGISTERED_PDF_FONT:
        return _REGISTERED_PDF_FONT, _REGISTERED_PDF_BOLD_FONT

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return "Helvetica", "Helvetica-Bold"

    search_paths = []

    # 1. Media directory (user uploaded fonts)
    media_dir = getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media"))
    if os.path.exists(media_dir):
        search_paths.extend(glob.glob(os.path.join(media_dir, "**", "*.ttf"), recursive=True))
        search_paths.extend(glob.glob(os.path.join(media_dir, "**", "*.otf"), recursive=True))

    # 2. Static fonts directory
    static_fonts = os.path.join(settings.BASE_DIR, "static", "fonts")
    if os.path.exists(static_fonts):
        preferred = ["arial.ttf", "arialbd.ttf", "tahoma.ttf", "amiri-regular.ttf", "cairo-regular.ttf", "ARIAL.TTF"]
        for p in preferred:
            fp = os.path.join(static_fonts, p)
            if os.path.exists(fp):
                search_paths.append(fp)
        search_paths.extend(glob.glob(os.path.join(static_fonts, "*.ttf")))

    # 3. Windows system fonts fallback
    win_fonts = ["C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\tahoma.ttf", "C:\\Windows\\Fonts\\calibri.ttf", "C:\\Windows\\Fonts\\seguiemj.ttf"]
    for wf in win_fonts:
        if os.path.exists(wf):
            search_paths.append(wf)

    # 4. Linux system fonts fallback
    linux_fonts = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    search_paths.extend(linux_fonts)

    # Find first existing font path
    chosen_path = None
    for sp in search_paths:
        if os.path.exists(sp) and os.path.isfile(sp):
            chosen_path = sp
            break

    if chosen_path:
        try:
            pdfmetrics.registerFont(TTFont("ArabicFont", chosen_path))
            _REGISTERED_PDF_FONT = "ArabicFont"

            # Check for bold font
            bold_path = os.path.join(os.path.dirname(chosen_path), "arialbd.ttf")
            if not os.path.exists(bold_path):
                bold_path = os.path.join(settings.BASE_DIR, "static", "fonts", "arialbd.ttf")
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("ArabicFont-Bold", bold_path))
                _REGISTERED_PDF_BOLD_FONT = "ArabicFont-Bold"
            else:
                _REGISTERED_PDF_BOLD_FONT = "ArabicFont"

            return _REGISTERED_PDF_FONT, _REGISTERED_PDF_BOLD_FONT
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold"


def is_already_reshaped(text):
    """Checks if text contains Arabic Presentation Forms (already reshaped)."""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[\uFB50-\uFDFF\uFE70-\uFEFF]', text))


def has_arabic_text(text):
    """Checks if a string contains raw unreshaped Arabic Unicode characters."""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F]', text))


def process_pdf_text(text):
    """
    Processes text for ReportLab PDF rendering:
    If text contains unreshaped Arabic characters, reshapes letters and applies BiDi direction.
    Idempotent: will not re-flip text that has already been reshaped.
    Handles dates with Arabic month names (e.g. 01-يوليو-2026) so month names are not flipped backwards.
    """
    if text is None:
        return ""
    text_str = str(text)
    if not text_str or is_already_reshaped(text_str):
        return text_str

    if has_arabic_text(text_str):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display

            date_match = re.match(
                r"^([^\u0600-\u06FF]*?\b\d{1,4}[-/ ])([^\d\s\-/]+)([-/ ]\d{1,4}\b.*)$",
                text_str,
            )
            if date_match and has_arabic_text(date_match.group(2)):
                prefix = date_match.group(1)
                arabic_month = date_match.group(2)
                suffix = date_match.group(3)
                prefix_proc = process_pdf_text(prefix) if has_arabic_text(prefix) else prefix
                suffix_proc = process_pdf_text(suffix) if has_arabic_text(suffix) else suffix
                bidi_month = get_display(arabic_reshaper.reshape(arabic_month))
                return f"{prefix_proc}{bidi_month}{suffix_proc}"

            reshaped = arabic_reshaper.reshape(text_str)
            return get_display(reshaped)
        except Exception:
            return text_str
    return text_str
