"""Shared vocabulary (en + ar) and text normalisation for the router.

Every regex here is written against *normalised* text (see norm()): lowercase, Arabic
diacritics/tatweel removed, alef/ya/ta-marbuta variants folded, Arabic-Indic digits -> ASCII.
"""

from __future__ import annotations

import re
from functools import lru_cache

_AR_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def norm(text: str) -> str:
    q = _AR_DIACRITICS.sub("", str(text or "")).translate(_FOLD).translate(_DIGITS).lower()
    return re.sub(r"[ \t\r\f\v]+", " ", q).strip()


def language(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    return "ar" if sum(1 for c in letters if "\u0600" <= c <= "\u06ff") / len(letters) > 0.3 else "en"


@lru_cache(maxsize=512)
def rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


# Words that mean "think / advise / compare" -> the model's job, not a lookup.
ANALYTIC = rx(
    r"\b(compar\w*|versus|vs|trend|trends|why|forecast|predict\w*|growth|explain\w*|reason|advice|advise|"
    r"recommend\w*|suggest\w*|insights?|analy[sz]\w*|improv\w*|should|budget\w*|save|saving|reduce|cut|"
    r"what if|scenario|simulat\w*|how can|how do i|how to|plan|should i invest|invest(?:ment)? (?:advice|strategy|plan)|good time|better to|worth it|afford)\b"
    r"|قارن|مقارنه|لماذا|ليه|علاش|توقع|توقعات|نصيحه|انصحني|اشرح|حلل|تحليل|كيف اوفر|كيف يمكنني|هل يجب|هل ينفع|"
    r"اقتراح|اقترح|اتجاه|ميزانيه|استثمر|ينفع"
)
ACTION = rx(r"^\s*(please\s+)?(add|create|delete|remove|update|edit|transfer|pay|record|change|set)\b|^\s*(اضف|احذف|امسح|عدل|حول|سجل)\b")

# Same as ANALYTIC but "budget"/"ميزانية" alone is a lookup when the question is ABOUT budgets
# ("how much of my food budget is left"); advice words (should, reduce, how can...) still fall through.
ANALYTIC_LOOKUP_BUDGET = rx(ANALYTIC.pattern.replace("budget\\w*|", "").replace("|ميزانيه", "") + r"|\bكيف\b")

# Currency words -> ISO code (normalised Arabic).
CURRENCIES: dict[str, str] = {
    "usd": "USD", "dollar": "USD", "dollars": "USD", "buck": "USD", "bucks": "USD", "دولار": "USD", "الدولار": "USD", "دولارات": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR", "يورو": "EUR", "اليورو": "EUR",
    "gbp": "GBP", "sterling": "GBP", "الاسترليني": "GBP", "استرليني": "GBP",
    "sar": "SAR", "riyal": "SAR", "riyals": "SAR", "ريال": "SAR", "الريال": "SAR",
    "aed": "AED", "dirham": "AED", "dirhams": "AED", "درهم": "AED", "الدرهم": "AED",
    "kwd": "KWD", "dinar": "KWD", "دينار": "KWD", "الدينار": "KWD",
    "qar": "QAR", "egp": "EGP", "جنيه": "EGP", "الجنيه": "EGP", "pound": "EGP", "pounds": "EGP",
    "chf": "CHF", "jpy": "JPY", "cad": "CAD", "aud": "AUD", "try": "TRY", "cny": "CNY", "inr": "INR", "bhd": "BHD", "omr": "OMR", "jod": "JOD",
}
_CUR_RE = re.compile(r"(?<![a-z\u0600-\u06ff])(" + "|".join(sorted(map(re.escape, CURRENCIES), key=len, reverse=True)) + r")(?![a-z\u0600-\u06ff])")


def find_currencies(q: str) -> list[str]:
    """Ordered, de-duplicated ISO codes mentioned in normalised text."""
    seen: list[str] = []
    for m in _CUR_RE.finditer(q):
        code = CURRENCIES[m.group(1)]
        if code not in seen:
            seen.append(code)
    return seen


KARAT_RE = re.compile(r"(?<!\d)(\d{2})\s*-?\s*(?:k|kt|karat|carat|k\.)\b|(?:عيار|karat|carat)\s*(\d{2})(?!\d)|(?<!\d)(\d{2})\s*قيراط")
BUY_RE = rx(r"\b(buy|buying|purchase|bid)\b|شراء|اشتري|يشتري")
SELL_RE = rx(r"\b(sell|selling|ask|offer)\b|بيع|ابيع|يبيع")
MID_RE = rx(r"\b(mid|middle|average rate)\b|متوسط")
TIME_HINT = rx(r"\b(20\d\d|ago|since|before|after|ended|ending|quarter|week|weeks|yesterday|semester|half|q[1-4])\b|منذ|قبل|بعد|اسبوع|ربع")
N_RE = rx(r"\b(?:last|latest|recent|past|top|first)\s+(\d{1,3})\b|(?:اخر|اعلي|اكبر)\s+(\d{1,3})")
