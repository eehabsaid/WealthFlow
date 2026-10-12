"""Download links for engine answers: when the question also asks to export ("... and export it in
excel sheet"), the instant answer ends with a link to a server-built .xlsx. The model never writes
the link and never claims it cannot export. Salary only for now (GET /api/salary/export/).
"""

from __future__ import annotations

import re
from .labels import t
from .lexicon import norm
from .spec import QueryRequest, QueryResult

_EXPORT_RE = re.compile(
    r"\bexcel\b|\bxlsx?\b|\bspreadsheet\b|\bexport\w*|\bdownload\w*|\btableur\b|\bt[eé]l[eé]charg\w*|\bherunterlad\w*|"
    r"اكسل|اكسيل|تصدير|صدر\w*|تحميل|نزل\w*"
)
_SALARY_URL = "/api/salary/export/"


def wants_export(text: str) -> bool:
    return bool(_EXPORT_RE.search(norm(text)))


def salary_export_url(years: list[int], lang: str) -> str:
    query = (f"years={','.join(str(y) for y in years)}&" if years else "") + f"lang={lang}"
    return f"{_SALARY_URL}?{query}"


def export_footer(capability: str, req: QueryRequest, result: QueryResult, text: str) -> str:
    """Markdown link line to append to the rendered answer, or '' (no export asked / not supported / nothing to export)."""
    if capability != "salary" or not (result.rows or result.facts) or not wants_export(text):
        return ""
    years = sorted({y for y, _ in req.periods})
    return f"[{t(req.lang, 'sal_export')}]({salary_export_url(years, req.lang)})"


def with_export_link(content: str, footer: str) -> str:
    return f"{content}\n\n{footer}" if footer else content


__all__ = ["wants_export", "salary_export_url", "export_footer", "with_export_link"]
