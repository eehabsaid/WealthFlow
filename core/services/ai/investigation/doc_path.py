"""Which way a requested document is written, decided from what the tools returned and never from a lone YES/NO.

guide   section by section from the LIVE app (one model call per screen / tab group, see compose_sections.py)
single  one call from the evidence the tools returned (a report on the user's own data)

A document may only be written in one call when that evidence holds the user's own rows (app_data_query, app_computed_figures,
or a generate_file dataset). A table list (app_data_models) or no tool output at all is not evidence of anything to report on,
so the guide path runs whatever the one-word classifier said: the classifier is an extra signal, not the decision.
In the App domain the user's data tools are not offered, so rows can never exist there and the classifier decides as before."""

from __future__ import annotations

import logging

from core.services.ai.domains import APP

logger = logging.getLogger("core.ai.pipeline")
ROW_TOOLS = ("app_data_query", "app_computed_figures")   # tools whose result is the user's own rows / ready-made figures


YES_WORDS = ("YES", "Y", "نعم", "اجل", "أجل", "OUI", "JA", "SI", "SÍ")   # the one-word question is answered in the user's language too
NO_WORDS = ("NO", "N", "لا", "NON", "NEIN")


def yes_no(word: str) -> bool | None:
    """True / False for a one-word answer in English, Arabic, French, German or Spanish; None when it is neither (ask again)."""
    token = (word or "").strip().strip(".!:\"'` ").upper().split(" ")[0] if (word or "").strip() else ""
    return True if token in YES_WORDS else False if token in NO_WORDS else None


def evidence_tools(out) -> list[str]:
    return list(dict.fromkeys(name for name, _, _ in (getattr(out, "results", None) or [])))


def has_user_rows(out) -> bool:
    for name, _, text in getattr(out, "results", None) or []:
        if name in ROW_TOOLS and not str(text).lstrip().startswith('{"error"'):
            return True
    for step in getattr(out, "steps", None) or []:
        args = step.get("arguments") if step.get("tool") == "generate_file" and step.get("status") == "success" else None
        if isinstance(args, dict) and (args.get("dataset") or args.get("datasets")):
            return True
    return False


def choose_path(out, classifier: bool | None, domain: str = "", own_file: bool = False) -> tuple[str, str]:
    """("guide" | "single", reason). `own_file` (the model already built a file itself) changes nothing: a file written from no
    evidence is exactly the invented guide this rule exists to stop (an Ask run without reasoning wrote one in 2 minutes)."""
    if classifier:
        return "guide", "classifier_yes"
    if domain == APP:
        return "single", "app_domain_classifier_no"
    if has_user_rows(out):
        return "single", "user_rows_in_evidence"
    return "guide", "no_user_rows_in_evidence"


def log_path(path: str, reason: str, classifier: bool | None, out) -> None:
    """One line per document (WARNING on purpose: the project has no LOGGING config, so INFO is hidden)."""
    logger.warning("[AI-DOC] path=%s reason=%s classifier=%s evidence_tools=%s", path, reason,
                   "n/a" if classifier is None else "YES" if classifier else "NO", evidence_tools(out))
