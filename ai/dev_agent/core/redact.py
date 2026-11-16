"""One redactor for everything that is written for training: secrets and tokens always; emails, phone numbers and amounts that carry a currency.

The old phone rule (any run of 9+ digits, spaces, dashes and brackets) masked plain numbers, dates and timestamps ("2026-11-13", "20261113123045",
"100 200 300 400", a 10-digit id) as ***REDACTED***, which wrecks source code and tool output. A number is now masked only when it is phone-shaped
(+country code, area code in brackets, 3-3-4 groups, an Egyptian mobile) or has a currency symbol/code next to it. Plain amounts such as 1250.50 are
never masked. Hashes (exactly 40 or 64 hex characters) are not secrets either: tool results carry file shas. Pure functions, no I/O, no Django."""

from __future__ import annotations

import re

MASK = "***REDACTED***"

# name = "value", name: 'value', "name": "value" and the same inside JSON-escaped text (\"name\": \"value\"), which is how tool results reach the model
_SECRET_ASSIGN = re.compile(
    r"""(?ix)(\b[\w.]*(?:secret|password|passwd|api[_-]?key|token|private[_-]?key|client[_-]?secret|hmac|salt)[\w.]*
    (?:\\*['"])?\s*[:=]\s*)(\\*['"])(?!\s*\2)(?:(?!\2).)+\2""")
# A stand-alone token is either base64-like (capital + small letter + digit, may contain + / _ -) or a long lowercase/digit run without any separator. A long
# path, slug, snake_case name or task id ("coding_agent/tasks/20261114-210732-how-do-x/events") is neither: no capital letter, or it has separators.
_LONG_TOKENS = (
    re.compile(r"\b(?=[A-Za-z0-9+/_-]*\d)(?=[A-Za-z0-9+/_-]*[a-z])(?=[A-Za-z0-9+/_-]*[A-Z])[A-Za-z0-9+/_-]{40,}\b"),
    re.compile(r"\b(?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{40,}\b"),
)
_HASH = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
_KEYLIKE = re.compile(r"\b(?:sk|pk|ghp|xox[a-z])[-_][A-Za-z0-9_-]{12,}")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONES = (
    re.compile(r"(?<![\w.+])\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}(?![\w-])"),    # +20 100 123 4567, +1-555-123-4567
    re.compile(r"(?<![\w.])\(\d{2,4}\)[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?![\w-])"),                  # (02) 3456 7890
    re.compile(r"(?<![\w.-])\d{3}[\s.-]\d{3}[\s.-]\d{4}(?![\w-])"),                              # 555-123-4567
    re.compile(r"(?<![\w.])(?:\+?20|0020)?[\s-]?01[0125][\s-]?\d{4}[\s-]?\d{4}(?![\w-])"),     # Egyptian mobile
)
_CUR = r"(?:USD|EGP|EUR|GBP|SAR|AED|KWD|QAR)"
_MONEY = (
    re.compile(r"(?<![\w.])[$£€]\s?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{3,})(?![\w.])"),   # $42.50, $1,200, $100; not $1 / $12 (regex groups, shell args)
    re.compile(rf"(?<![\w.])\d[\d,]*(?:\.\d+)?\s?{_CUR}(?![\w.])", re.I),                         # 5,000 EGP
    re.compile(rf"(?<![\w.]){_CUR}\s?\d[\d,]*(?:\.\d+)?(?![\w.])"),                               # EGP 5,000
)


def mask_secrets(text: str) -> tuple[str, int]:
    """Credential-looking assignments, key-looking tokens and long random tokens (not plain hashes). Returns (text, spots masked)."""
    hits = 0
    text, n = _SECRET_ASSIGN.subn(lambda m: f"{m.group(1)}{m.group(2)}{MASK}{m.group(2)}", text)
    hits += n
    text, n = _KEYLIKE.subn(MASK, text)
    hits += n

    def token(match):
        nonlocal hits
        if _HASH.fullmatch(match.group(0)):
            return match.group(0)
        hits += 1
        return MASK

    for pattern in _LONG_TOKENS:
        text = pattern.sub(token, text)
    return text, hits


def mask_pii(text: str, money: bool = True) -> tuple[str, int]:
    """Emails, phone-shaped numbers and (when `money`) amounts with a currency. Plain numbers, dates and ids stay as they are."""
    hits = 0
    for pattern in (_EMAIL, *_PHONES, *(_MONEY if money else ())):
        text, n = pattern.subn(MASK, text)
        hits += n
    return text, hits


def redact(text: str, pii: bool = True, money: bool = True) -> tuple[str, int]:
    """(redacted text, number of masked spots). Secrets are always masked; `pii=False` leaves emails/phones/amounts alone."""
    text, hits = mask_secrets(text)
    if not pii:
        return text, hits
    text, more = mask_pii(text, money)
    return text, hits + more


def redact_value(value, pii: bool = True, money: bool = True) -> tuple[object, int]:
    """Redact every string inside a JSON-like value (dict keys are kept). Returns (copy, number of masked spots)."""
    if isinstance(value, str):
        return redact(value, pii, money)
    if isinstance(value, dict):
        out, total = {}, 0
        for key, item in value.items():
            out[key], n = redact_value(item, pii, money)
            total += n
        return out, total
    if isinstance(value, (list, tuple)):
        items, total = [], 0
        for item in value:
            new, n = redact_value(item, pii, money)
            items.append(new)
            total += n
        return items, total
    return value, 0
