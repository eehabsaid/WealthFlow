"""Asks generated questions through the REAL chat endpoint (Agent mode), twice each, records the runs and judges them.

Runs from the command line, never inside the web server. The conversations it creates are deleted afterwards, so the
user's chat history stays clean; the AgentTrace rows are what remains."""

from __future__ import annotations

import json
from collections import Counter
from typing import Callable

from django.test import Client

from ai_training.models import AgentTrace
from core.models import AIConversation

from core.services.ai.domains import BUSINESS

from . import context, judges

CHAT_URL = "/api/financial-advisor/ai/chat/"
ATTEMPTS = 2


def ask(user, case, attempt: int) -> tuple[AgentTrace | None, str]:
    """One run of one question as `user`. Returns (trace, problem); problem is "" when a trace was recorded."""
    client = Client(SERVER_NAME="localhost")
    client.force_login(user)
    with context.collecting(case_key=case.key, attempt=attempt, expected=case.expected) as ctx:
        res = client.post(CHAT_URL, json.dumps({"message": case.question, "chat_mode": "agent", "question_domain": BUSINESS}), content_type="application/json")
    try:
        data = res.json()
    except ValueError:
        data = {}
    if data.get("conversation_id"):
        AIConversation.objects.filter(pk=data["conversation_id"], user=user).delete()
    if not ctx["saved"]:
        return None, f"no trace (HTTP {res.status_code}): {str(data.get('error') or data.get('message') or '')[:120]}"
    return AgentTrace.objects.get(pk=ctx["saved"][-1]), ""


def judge_case(traces: list[AgentTrace]) -> list[str]:
    """Reasons to drop the whole case (empty = every run passed and the repeat gave the same figures)."""
    reasons = [r for t in traces for r in judges.judge_attempt(t)]
    return sorted(set(reasons)) or judges.repeat_check(traces, traces[0].expected if traces else None)


def run(user, cases, *, attempts: int = ATTEMPTS, log: Callable[[str], None] = print) -> dict:
    summary, reasons = Counter(), Counter()
    for i, case in enumerate(cases, 1):
        traces, problem = [], ""
        for attempt in range(1, attempts + 1):
            trace, problem = ask(user, case, attempt)
            if trace is None:
                break
            traces.append(trace)
        drop = [problem] if problem else judge_case(traces)
        verdict = AgentTrace.DROPPED if drop else AgentTrace.KEPT
        for t in traces:
            t.verdict, t.drop_reasons = verdict, drop
            t.save(update_fields=["verdict", "drop_reasons"])
        summary[verdict] += 1
        reasons.update(r.split(":")[0] for r in drop)
        log(f"[{i}/{len(cases)}] {verdict.upper()} {case.key} {', '.join(drop)}")
    return {"cases": len(cases), "kept": summary[AgentTrace.KEPT], "dropped": summary[AgentTrace.DROPPED], "reasons": dict(reasons)}
