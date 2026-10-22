"""Which way a requested document is written, decided from what the tools returned and never from a lone YES/NO.

guide   section by section from the LIVE app (one model call per screen / tab group, see compose_sections.py)
single  one call from the evidence the tools returned (a report on the user's own data)

A document may only be written in one call when that evidence holds the user's own rows (app_data_query, app_computed_figures,
or a generate_file dataset). A table list (app_data_models), an empty query, or no tool output is not evidence of data to report
on, so the app guide is the fallback. Live screen evidence outranks the one-word classifier; actual user rows outrank a false
positive. In the App domain, business-data evidence is unavailable, so the existing domain policy still applies."""

from __future__ import annotations

import json
import logging
import re

from core.services.ai.domains import APP

logger = logging.getLogger("core.ai.pipeline")
ROW_TOOLS = ("app_data_query", "app_computed_figures")   # tools whose result is the user's own rows / ready-made figures
APP_GUIDE_TOOLS = ("app_routes",)
_HTML_FORM = re.compile(r"<form\b[\s\S]*?</form>", re.IGNORECASE)
_FORM_CONTROL = re.compile(r"<(?:input|select|textarea)\b", re.IGNORECASE)


YES_WORDS = ("YES", "Y", "نعم", "اجل", "أجل", "OUI", "JA", "SI", "SÍ")   # the one-word question is answered in the user's language too
NO_WORDS = ("NO", "N", "لا", "NON", "NEIN")


def yes_no(word: str) -> bool | None:
    """True / False for a one-word answer in English, Arabic, French, German or Spanish; None when it is neither (ask again)."""
    token = (word or "").strip().strip(".!:\"'` ").upper().split(" ")[0] if (word or "").strip() else ""
    return True if token in YES_WORDS else False if token in NO_WORDS else None


def evidence_tools(out) -> list[str]:
    return list(dict.fromkeys(name for name, _, _ in (getattr(out, "results", None) or [])))


def _data_result(text: str) -> dict:
    try:
        result = json.loads(str(text))
    except (TypeError, ValueError):
        return {}
    if isinstance(result, dict) and "ok" in result and "data" in result:
        if not result["ok"]:
            return {}
        result = result["data"]
    return result if isinstance(result, dict) and not result.get("error") else {}


def has_user_rows(out) -> bool:
    for name, _, text in getattr(out, "results", None) or []:
        if name not in ROW_TOOLS:
            continue
        data = _data_result(text)
        if name == "app_data_query":
            if data.get("rows") or data.get("groups"):
                return True
            if data.get("total_matching", 0) and data.get("result") is not None:
                return True
            raw = str(text or "").strip()
            if raw and not raw.startswith(("{", "[")):
                return True
        elif data.get("figures") not in (None, {}, []):
            return True
    for step in getattr(out, "steps", None) or []:
        args = step.get("arguments") if step.get("tool") == "generate_file" and step.get("status") == "success" else None
        if isinstance(args, dict) and (args.get("dataset") or args.get("datasets")):
            return True
    return False


def has_app_structure_evidence(out) -> bool:
    return any(name in APP_GUIDE_TOOLS and not str(text).lstrip().startswith('{"error"')
               for name, _, text in getattr(out, "results", None) or [])


def is_standalone_html_code(out, user=None) -> bool:
    """A standalone page is code; an HTML draft covering live screens is an app guide."""
    sources = [str(getattr(out, "content", "") or "")]
    for step in getattr(out, "steps", None) or []:
        args = step.get("arguments") if step.get("tool") == "generate_file" else None
        if isinstance(args, dict) and isinstance(args.get("content"), str):
            sources.append(args["content"])
    for source in sources:
        if any(_FORM_CONTROL.search(match.group(0)) for match in _HTML_FORM.finditer(source)):
            return True
        if not re.search(r"<html\b", source, re.IGNORECASE) or user is None:
            continue
        from .compose_sections import units

        titles = {unit["title"] for unit in units(user)}
        needed = max(3, (len(titles) + 4) // 5)
        matched = sum(title.casefold() in source.casefold() for title in titles)
        if matched < needed:
            return True
    return False


def choose_path(out, classifier: bool | None, domain: str = "", own_file: bool = False) -> tuple[str, str]:
    """("guide" | "single", reason). `own_file` (the model already built a file itself) changes nothing: a file written from no
    evidence is exactly the invented guide this rule exists to stop (an Ask run without reasoning wrote one in 2 minutes)."""
    if has_app_structure_evidence(out):
        return "guide", "app_structure_in_evidence"
    if has_user_rows(out):
        return "single", "user_rows_in_evidence"
    if domain == APP and classifier:
        return "guide", "app_domain_guide_refused"
    if domain == APP:
        return "single", "app_domain_classifier_no"
    if classifier:
        return "guide", "classifier_yes"
    return "guide", "no_user_rows_in_evidence"


def log_path(path: str, reason: str, classifier: bool | None, out) -> None:
    """One line per document (WARNING on purpose: the project has no LOGGING config, so INFO is hidden)."""
    logger.warning("[AI-DOC] path=%s reason=%s classifier=%s evidence_tools=%s", path, reason,
                   "n/a" if classifier is None else "YES" if classifier else "NO", evidence_tools(out))
