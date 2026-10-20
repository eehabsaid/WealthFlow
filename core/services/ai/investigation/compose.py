"""Guarantee for "write me a document": the file must hold the document, never the model's "let me write it" sentence.

A model that researched with the tools but then stopped without calling generate_file leaves a short announcement as its
answer, and that text would become the file. No phrase list can catch every wording, so the rule is structural: a document
was requested, no generate_file call succeeded and the answer is short -> the app writes the document itself.

Two ways, chosen by the model with a one-word question (no phrase list):
  * a guide to the app itself -> section by section, one model call per screen/tab group of the LIVE app (a local model with a
    small context window cannot write 20 screens in one reply, and was cutting the guide off after a third of it). A section
    the model fails to write, or that does not fit the time budget, is filled from the app's own screen list.
  * any other document (a report on the user's data) -> one call from the evidence the tools returned.
A guide asked for in another language is written in English and then translated chunk by chunk (compose_translate.py).
Every call gets the document output-token limit (Settings > AI Advisor) so a reply is not cut off at the default of a chat answer;
a reply the limit still cut off is never trusted: the half-written last tab is rewritten alone, a half translation is redone."""

from __future__ import annotations

import logging
import time

from .actions import strip_think
from core.services.ai.domain_scope import no_info
from core.services.ai.domains import APP

from .compose_quality import norm, replace_blocks, report, sanitize, thin_tabs
from .compose_sections import dedupe_headings, knowledge, missing_tabs, tab_fallback, units
from .compose_translate import target_language, translate_markdown, uses_latin_script
from .refusal import is_refusal

MIN_DOC_CHARS = 1500      # a real guide/report is longer than this; shorter text is an announcement or a stub
MIN_ACCEPT_CHARS, MIN_SECTION_CHARS, TIMEOUT_S = 400, 120, 240
_ABOUT_APP = ("Answer with exactly one word, YES or NO. Is the user asking for documentation of the application itself (a user guide, "
              "manual or description of its screens and features), rather than a report or analysis of their own financial data?")


def generated_file(steps: list) -> bool:
    return any(s.get("tool") == "generate_file" and s.get("status") == "success" for s in steps or [])


def needs_document(out) -> bool:
    """No file was generated and the answer is a stub, or the model's generate_file call was cut off (its text is a partial document)."""
    return not generated_file(out.steps) and (len((out.content or "").strip()) < MIN_DOC_CHARS or out.reason == "truncated_call")


def _ask(provider, out, system: str, user_content: str, deadline: float, temperature: float = 0.2) -> str:
    from core.services.ai.agent.settings import document_max_tokens

    out.llm_calls += 1
    out.cut_off = False
    limit = document_max_tokens(provider)
    try:
        res = provider.generate([{"role": "system", "content": system}, {"role": "user", "content": user_content}], tools=None,
                                temperature=temperature, max_tokens=limit, timeout=int(max(20, min(TIMEOUT_S, deadline - time.monotonic()))))
    except Exception:  # noqa: BLE001 - the caller falls back
        return ""
    if not isinstance(res, dict) or res.get("error"):
        return ""
    used = res.get("completion_tokens")
    out.cut_off = isinstance(used, int) and used >= 0.97 * limit   # stopped by the limit, not because it was finished
    return strip_think(res.get("content")).strip()


def _without_partial_tab(text: str) -> str:
    """A section the output limit cut off ends inside its last tab: that tab is dropped (missing_tabs then rewrites it alone)."""
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    return "\n".join(lines[:heads[-1]]).rstrip() if len(heads) > 1 else text


def _about_the_app(provider, user_text: str, out, deadline: float) -> bool:
    return _ask(provider, out, _ABOUT_APP, user_text, deadline, temperature=0).upper().startswith("YES")


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def _heading(text: str, unit: dict) -> str:
    """The section as Markdown under exactly one "## title": the model's own first heading is replaced by the unit title, every
    other H1/H2 becomes H3, and a heading that only repeats the screen's name is dropped (no "Settings / Settings")."""
    same = {_norm(unit["title"]), _norm(unit["page"])}
    head = unit.get("heading", unit["title"])
    out = [f"## {head}", ""] if head else []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            name = stripped.lstrip("#").strip()
            if _norm(name) in same:
                continue
            if stripped.startswith(("# ", "## ")):
                line = f"### {name}"
        elif not stripped and not any(x.strip() for x in out[2 if head else 0:]):
            continue
        out.append(line)
    return "\n".join(out).rstrip()


logger = logging.getLogger("core.ai.pipeline")


def _qa(markdown: str, language: str = "") -> str:
    """The guide, with its quality report in the log (a non-zero count means the gate could not repair something)."""
    found = report(markdown)
    (logger.warning if any(v for k, v in found.items() if k != "chapters") else logger.info)("[AI-GUIDE-QA] %s language=%s", found, language or "en")
    return markdown


def _tab_section(provider, user, user_text: str, out, unit: dict, tab: dict, instructions: str, deadline: float) -> str:
    """One tab the section skipped: written alone (small prompt); the app's own tab list when the model cannot or time is up."""
    text = ""
    if time.monotonic() < deadline - 20:
        text = _ask(provider, out, instructions, f"REQUEST:\n{user_text}\n\nWrite ONLY this sub-section, starting with the line \"### {tab['name']}\": "
                    f"what the tab is for and the steps to use each action.\n\nTAB:\n{tab}\n\nAPP GUIDE:\n{knowledge(user, unit, tab)}", deadline)
    if len(text) < MIN_SECTION_CHARS or is_refusal(text, True):
        return tab_fallback(tab)
    return text if text.lstrip().startswith("###") else f"### {tab['name']}\n\n{text}"


def _guide(provider, user, user_text: str, out, instructions: str, budget_s: int, progress) -> str:
    started = time.monotonic()
    deadline = started + budget_s
    plan = units(user)
    intro = _ask(provider, out, instructions, f"REQUEST:\n{user_text}\n\nWrite ONLY the document title (one line starting with '# ') and a short introduction "
                 f"(3-5 sentences) of the guide. Screens: {', '.join(dict.fromkeys(u['title'] for u in plan))}", deadline)
    parts = [intro if intro.startswith("# ") and len(intro) > 30 else f"# User guide\n\n{intro}".rstrip()]
    for n, unit in enumerate(plan, 1):
        if progress:
            progress(n, len(plan), unit["label"], started)
        text = ""
        if time.monotonic() < deadline - 20:
            part = unit.get("part") or (1, 1)
            more = f" It is part {part[0]} of {part[1]} of one chapter: write only the tabs listed, without a chapter title or introduction." if part[1] > 1 else ""
            text = _ask(provider, out, instructions, f"REQUEST:\n{user_text}\n\nWrite ONLY this section: \"{unit['title']}\". Cover every tab and "
                        f"action listed, with the steps to use them.{more}\n\nSCREEN:\n{unit['evidence']}\n\nAPP GUIDE:\n{knowledge(user, unit)}", deadline)
        if out.cut_off:
            text = _without_partial_tab(text)
        if len(text) < MIN_SECTION_CHARS or is_refusal(text, True):
            parts.append(unit["fallback"])
            continue
        section = _heading(text, unit)
        section = replace_blocks(section, thin_tabs(unit, section, tab_fallback), tab_fallback)   # a stub where the app documents more
        for tab in missing_tabs(unit, section):   # the model dropped these tabs: nothing may be missing from the guide
            section += "\n\n" + _tab_section(provider, user, user_text, out, unit, tab, instructions, deadline)
        parts.append(section)
    protect = frozenset({norm(u["page"]) for u in plan} | {norm(t) for u in plan for t in u["tabs"]} - {""})
    return _qa(sanitize(dedupe_headings("\n\n".join(parts)), protect=protect))


def _single(provider, user_text: str, out, instructions: str, ctx_chars: int, deadline: float) -> str:
    budget = max(6000, ctx_chars - 4000)
    evidence = "\n\n".join(f"[{name} {str(args)[:120]}]\n{text}" for name, args, text in (out.results or []))[:budget]
    text = _ask(provider, out, instructions, f"REQUEST:\n{user_text}\n\nEVIDENCE:\n{evidence or '(no tool results)'}", deadline)
    return text if len(text) >= MIN_ACCEPT_CHARS and not is_refusal(text, True) else ""


def drop_model_drafts(steps: list) -> None:
    """The app wrote the guide itself: the text the model put in its own generate_file calls is not the file's content any more
    (the download is built from the saved answer). Datasets and tables the calls carry stay."""
    for step in steps or []:
        args = step.get("arguments") if step.get("tool") == "generate_file" else None
        if isinstance(args, dict):
            args.pop("content", None)


def compose_document(provider, user_text: str, out, ctx_chars: int = 24000, user=None, progress=None, guide_only: bool = False, domain: str = "") -> str:
    """The full document text, or "" when the model could not produce one (the caller keeps the original answer).
    guide_only: the model already made a file with generate_file; only a guide to the app itself is rewritten by the app.
    domain: the user guide describes the application for business users, so it belongs to the Business domain only; a guide
    requested in the App domain gets the short no-information answer."""
    from core.services.ai.agent.instructions import effective_document_instructions
    from core.services.ai.agent.settings import document_budget_s

    instructions, budget_s = effective_document_instructions(), document_budget_s()
    deadline = time.monotonic() + budget_s
    if user is not None and _about_the_app(provider, user_text, out, deadline):
        if domain == APP:
            return no_info(user_text)
        def ask(system: str, content: str, temperature: float = 0.2) -> str:
            return _ask(provider, out, system, content, deadline, temperature)

        language = target_language(ask, user_text)
        if not language:
            return _guide(provider, user, user_text, out, instructions, budget_s, progress)
        english = _guide(provider, user, f"{user_text}\n\n[Write the document in English; it is translated into {language} afterwards.]",
                         out, instructions, int(budget_s * 0.45), progress)
        non_latin = not uses_latin_script(ask, language)
        return _qa(sanitize(translate_markdown(ask, lambda: bool(getattr(out, "cut_off", False)), english, language, deadline, progress, non_latin), english=False), language)
    if guide_only:
        return ""
    return _single(provider, user_text, out, instructions, ctx_chars, deadline)
