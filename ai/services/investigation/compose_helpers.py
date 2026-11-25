"""Document-need check, QA logging and draft cleanup helpers for compose."""

from __future__ import annotations

import logging


from ai.services.investigation.compose_quality import report


MIN_DOC_CHARS = 1500      # a real guide/report is longer than this; shorter text is an announcement or a stub


def generated_file(steps: list) -> bool:
    return any(s.get("tool") == "generate_file" and s.get("status") == "success" for s in steps or [])


def needs_document(out) -> bool:
    """No file was generated and the answer is a stub, or the model's generate_file call was cut off (its text is a partial document)."""
    return not generated_file(out.steps) and (len((out.content or "").strip()) < MIN_DOC_CHARS or out.reason == "truncated_call")


def _without_partial_tab(text: str) -> str:
    """A section the output limit cut off ends inside its last tab: that tab is dropped (missing_tabs then rewrites it alone)."""
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    return "\n".join(lines[:heads[-1]]).rstrip() if len(heads) > 1 else text
logger = logging.getLogger("ai.pipeline")


def _qa(markdown: str, language: str = "") -> str:
    """The guide, with its quality report in the log (a non-zero count means the gate could not repair something)."""
    found = report(markdown)
    (logger.warning if any(v for k, v in found.items() if k != "chapters") else logger.info)("[AI-GUIDE-QA] %s language=%s", found, language or "en")
    return markdown


def drop_model_drafts(steps: list) -> None:
    """The app wrote the guide itself: the text the model put in its own generate_file calls is not the file's content any more
    (the download is built from the saved answer). Datasets and tables the calls carry stay."""
    for step in steps or []:
        args = step.get("arguments") if step.get("tool") == "generate_file" else None
        if isinstance(args, dict):
            args.pop("content", None)
