"""remember: the agent proposes a durable finding (architecture, a confirmed business rule, a lesson) with the files that prove it.
It is only STAGED in the task ledger; capture writes it to memory when the task really finished (completed or answered), so a failed,
stopped or rejected task never leaves unverified claims behind."""

from __future__ import annotations

from ..memory import quality, store
from .registry import ToolError, tool

MAX_NOTES = 8


@tool("remember", "args {kind: architecture|rules|lessons, text, evidence: [files you READ this phase that prove it]}: keep a verified finding for future tasks "
      "(structure facts, confirmed business rules, lessons). No guesses, secrets or personal data. Saved only if the task finishes.")
def remember(ctx, args):
    kind, text = str(args.get("kind") or ""), str(args.get("text") or "")
    if kind not in ("architecture", "rules", "lessons"):
        raise ToolError("kind must be architecture, rules or lessons")
    evidence = [ctx.project.resolve(e)[0] for e in (args.get("evidence") or []) if isinstance(e, str)]
    if not evidence or any(e not in ctx.seen for e in evidence):
        raise ToolError("give `evidence`: the files you read in this phase that prove the finding (read them first)")
    try:
        body = store.clean(text)
    except store.MemoryRefused as exc:
        raise ToolError(str(exc)) from exc
    notes = ctx.ledger.data.setdefault("memory_notes", []) if ctx.ledger else []
    if len(notes) >= MAX_NOTES:
        raise ToolError(f"at most {MAX_NOTES} findings per task")
    if quality.duplicate(body, [n["text"] for n in notes if n["kind"] == kind]):
        return {"ok": True, "staged": False, "note": "already staged"}
    notes.append({"kind": kind, "text": body, "evidence": evidence[:5]})
    if ctx.ledger:
        ctx.ledger.save()
    return {"ok": True, "staged": True, "note": "saved to memory when the task finishes"}
