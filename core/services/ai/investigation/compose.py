"""Guarantee for "write me a document": the file must hold the document, never the model's "let me write it" sentence.

A model that researched with the tools but then stopped without calling generate_file leaves a short announcement as its
answer, and that text would become the file. No phrase list can catch every wording ("let me generate/compose/draft..."),
so the rule is structural: a document was requested, no generate_file call succeeded and the answer is short -> one
dedicated tool-free call writes the complete document from the evidence the tools returned."""

from __future__ import annotations

from .actions import strip_think
from .refusal import is_refusal

MIN_DOC_CHARS = 1500      # a real guide/report is longer than this; shorter text is an announcement or a stub
MIN_ACCEPT_CHARS = 400
TIMEOUT_S = 240
_SYSTEM = ("You write documents for the user of a personal-finance app. Write the COMPLETE document the user asked for now, in "
           "Markdown: a title (#), sections (##) with clear headings, short paragraphs, bullet lists and numbered steps where "
           "useful. Use only the evidence below (what the app's tools returned); do not invent features. Cover EVERY screen and "
           "area the evidence lists (each with its purpose and the steps to use it), plus getting started and settings when the "
           "evidence mentions them; do not stop after a few sections. Write in the language of the request. Output ONLY the document: no introduction, no 'let me', no 'here is', no questions, no links.")


def generated_file(steps: list) -> bool:
    return any(s.get("tool") == "generate_file" and s.get("status") == "success" for s in steps or [])


def needs_document(out) -> bool:
    return not generated_file(out.steps) and len((out.content or "").strip()) < MIN_DOC_CHARS


def _with_routes(user, out) -> list:
    """The tool results plus the app's full screen list (so the document covers every screen, not only what the model searched)."""
    results = list(out.results or [])
    if user is None or any(name == "app_routes" for name, _, _ in results):
        return results
    try:
        from core.services.ai.tools import validate_and_execute_tool

        _, res = validate_and_execute_tool("app_routes", {}, user)
        from .loop_helpers import result_text

        results.insert(0, ("app_routes", {}, result_text(res, 6000)))
    except Exception:  # noqa: BLE001 - extra evidence only
        pass
    return results


def compose_document(provider, user_text: str, out, ctx_chars: int = 24000, user=None) -> str:
    """The full document text, or "" when the model could not produce one (the caller keeps the original answer)."""
    budget = max(6000, ctx_chars - 4000)
    evidence = "\n\n".join(f"[{name} {str(args)[:120]}]\n{text}" for name, args, text in _with_routes(user, out))[:budget]
    messages = [{"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"REQUEST:\n{user_text}\n\nEVIDENCE:\n{evidence or '(no tool results)'}"}]
    out.llm_calls += 1
    try:
        res = provider.generate(messages, tools=None, temperature=0.2, timeout=TIMEOUT_S)
    except Exception:  # noqa: BLE001 - the caller keeps the original answer
        return ""
    text = strip_think((res or {}).get("content")) if isinstance(res, dict) and not res.get("error") else ""
    return text if len(text) >= MIN_ACCEPT_CHARS and not is_refusal(text, True) else ""
