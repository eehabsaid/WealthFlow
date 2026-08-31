"""
styles.py
=========
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). Builds the reportlab colors and ParagraphStyle
objects shared across the cover, summary, category and expense sections.
"""


def build_colors():
    from reportlab.lib import colors

    return {
        "navy": colors.HexColor("#000080"),
        "blue": colors.HexColor("#1a6ef5"),
        "green": colors.HexColor("#00d68f"),
        "red": colors.HexColor("#ff4d6d"),
        "grey": colors.HexColor("#7b97cc"),
        "white": colors.white,
    }


def build_styles(pdf_font, lang, palette):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    navy, blue = palette["navy"], palette["blue"]

    H1 = ParagraphStyle("H1", fontSize=22, textColor=blue, spaceAfter=15, alignment=TA_CENTER, fontName=pdf_font)
    H11 = ParagraphStyle("H11", fontSize=18, textColor=navy, spaceAfter=15, alignment=TA_CENTER, fontName=pdf_font)
    H2 = ParagraphStyle("H2", fontSize=14, textColor=navy, spaceAfter=4, spaceBefore=12, fontName=pdf_font)
    table_title = ParagraphStyle("TableTitle", parent=H2, alignment=TA_RIGHT if lang == "ar" else TA_LEFT)

    def cell_set(size, suffix=""):
        white = palette["white"]
        return {
            "L": ParagraphStyle(f"CellL{suffix}", fontName=pdf_font, fontSize=size, textColor=navy, alignment=TA_LEFT),
            "R": ParagraphStyle(f"CellR{suffix}", fontName=pdf_font, fontSize=size, textColor=navy, alignment=TA_RIGHT),
            "HL": ParagraphStyle(f"CellHL{suffix}", fontName=pdf_font, fontSize=size, textColor=white, alignment=TA_LEFT),
            "HR": ParagraphStyle(f"CellHR{suffix}", fontName=pdf_font, fontSize=size, textColor=white, alignment=TA_RIGHT),
        }

    footer = ParagraphStyle("F", fontSize=8, textColor=palette["grey"], alignment=TA_CENTER, fontName=pdf_font)

    return {
        "H1": H1,
        "H11": H11,
        "H2": H2,
        "table_title": table_title,
        "cell10": cell_set(10),
        "cell9": cell_set(9, "9"),
        "cell8": cell_set(8, "8"),
        "footer": footer,
    }
