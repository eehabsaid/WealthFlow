"""Dataset export: only traces that passed every judge, one per question, as JSONL in chat / tool-call format, plus a plain report.

Each line: {"messages": [system, user, (assistant tool_calls, tool result)*, assistant answer], "tools": [...]}.
The system message is the exact prompt the model ran with (so the editable Agent instructions are the only instructions);
the user message is exactly what the model received. Nothing is added or rewritten."""

from __future__ import annotations

import json
from collections import Counter

from ai_training.models import AgentTrace
from core.services.ai.investigation.loop_helpers import asked_text


def to_messages(trace: AgentTrace) -> list[dict]:
    msgs = [{"role": "system", "content": trace.system_prompt}, {"role": "user", "content": asked_text(trace.question, trace.hint)}]
    for n, step in enumerate(trace.steps, 1):
        call_id = f"call_{n}"
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": call_id, "type": "function",
                     "function": {"name": step["tool"], "arguments": step.get("arguments") or {}}}]})
        msgs.append({"role": "tool", "tool_call_id": call_id, "name": step["tool"], "content": step.get("result", "")})
    msgs.append({"role": "assistant", "content": trace.answer})
    return msgs


def kept_traces(owner=None):
    """The first kept run of every question (the repeat run proved it; exporting both would only duplicate it)."""
    seen, out = set(), []
    qs = AgentTrace.objects.filter(verdict=AgentTrace.KEPT).exclude(source=AgentTrace.SOURCE_EVAL).order_by("case_key", "attempt", "id")
    for t in qs.filter(owner=owner) if owner else qs:
        if (t.owner_id, t.case_key) not in seen:
            seen.add((t.owner_id, t.case_key))
            out.append(t)
    return out


def export_jsonl(path: str, owner=None) -> int:
    traces = kept_traces(owner)
    with open(path, "w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps({"messages": to_messages(t), "tools": t.tools}, ensure_ascii=False) + "\n")
    return len(traces)


def report(owner=None) -> dict:
    """Plain counts per question (not per run): kept, dropped, and why."""
    qs = AgentTrace.objects.filter(attempt=1).exclude(source=AgentTrace.SOURCE_EVAL)
    qs = qs.filter(owner=owner) if owner else qs
    reasons = Counter(r.split(":")[0] for t in qs.filter(verdict=AgentTrace.DROPPED) for r in (t.drop_reasons or ["unknown"]))
    return {"questions": qs.count(), "kept": qs.filter(verdict=AgentTrace.KEPT).count(), "dropped": qs.filter(verdict=AgentTrace.DROPPED).count(),
            "pending": qs.filter(verdict=AgentTrace.PENDING).count(), "drop_reasons": dict(reasons.most_common())}


def format_report(rep: dict) -> str:
    lines = [f"Questions asked: {rep['questions']}   Kept: {rep['kept']}   Dropped: {rep['dropped']}   Not judged yet: {rep['pending']}"]
    lines += [f"  dropped because {k}: {v}" for k, v in rep["drop_reasons"].items()]
    return "\n".join(lines)
