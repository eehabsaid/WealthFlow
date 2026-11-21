"""A user guide never contains an amount: no balance, price or total of the user (or of anyone) belongs in a description of the screens.

A model that is given one line to translate or one tab to describe can answer it instead ("List the items and their estimated
values" became "based on your data the items are: Gold Vault (87,500.00) ..."): an amount that is not in the text the model was
given is invented or leaked, so the piece is rejected and the documented text of the screen is used instead. Judged on the numbers
only, so it holds in every language and script (Arabic-Indic digits and separators are read as ordinary ones)."""

from __future__ import annotations

import re

AMOUNT = re.compile(r"\d[\d,]*\.\d+|\d{1,3}(?:,\d{3})+")   # 920.50, 175,000.00, 1,000 (a step number or a year is not an amount)
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")


def amounts(text: str) -> set[float]:
    out = set()
    for found in AMOUNT.findall(str(text or "").translate(_DIGITS)):
        try:
            out.add(float(found.replace(",", "")))
        except ValueError:
            continue
    return out


def invented_amounts(source: str, text: str) -> bool:
    """True when `text` holds an amount that `source` (what the model was given) does not."""
    return bool(amounts(text) - amounts(source))
