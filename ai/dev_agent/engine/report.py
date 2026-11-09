"""The final report, built from the ledger (what actually happened), never from the model's own claims. Written to tasks/<id>/report.md."""

from __future__ import annotations

from ai.dev_agent.core import fsutil
from ai.dev_agent.engine import verify


def build(ledger) -> str:
    d = ledger.data
    final = next((v for v in reversed(d["verification"]) if v["label"] == "final"), None)
    lines = [f"# Task {d['id']}", f"Goal: {d['goal']}", f"Status: {d['status'].upper()}" + (f" - {d['stop_reason']}" if d["stop_reason"] else ""), ""]
    if d.get("answer"):
        lines += ["## Answer (no file changes were made)", d["answer"], ""]
    lines.append("## Work done")
    for p in d["packages"]:
        lines.append(f"- {p['id']} {p['title']}: {p['status']}" + (f" - {p['summary']}" if p["summary"] else ""))
    lines += ["", "## Files changed (exact state)"]
    lines += [f"- {rel}: {f['state']}" + (f" ({f['detail']})" if f["detail"] else "") for rel, f in sorted(d["files"].items())] or ["- none"]
    lines += ["", "## Verification"]
    if final:
        lines.append(f"Overall: {verify.overall(final['results'])}")
        lines += [f"Checks: {verify.counts(final['results'])}", f"Automated tests: {verify.tests_line(final['results'])}", verify.e2e_line(final["results"])]
        lines += [f"- {r['step']}: {r['status']}" + (f" - {r['detail'].splitlines()[0][:160]}" if r["detail"] else "") for r in final["results"]]
    elif d["status"] == "answered":
        lines.append("Not applicable: no files were changed.")
    else:
        lines.append("Overall: NOT VERIFIED - the final checks did not run (the task did not finish).")
        last = d["verification"][-1] if d["verification"] else None
        if last:
            lines.append(f"Last checks run ({last['label']}):")
            lines += [f"- {r['step']}: {r['status']}" for r in last["results"]]
    lines += ["", "## Not run / open issues"]
    not_run = [r for r in (final["results"] if final else []) if r["status"] == "NOT RUN"]
    lines += [f"- NOT RUN: {r['step']} - {r['detail'].splitlines()[0][:200]}" for r in not_run]
    lines += [f"- Protected-file change proposed for you: {p['path']} - {p['text'][:300]}" for p in d["proposals"]]
    lines += [f"- Refused/not approved: {a['message']}" for a in d["approvals"] if not a["approved"]]
    if d["stop_reason"]:
        lines.append(f"- Stopped: {d['stop_reason']}")
    e2e_passed = bool(final) and any(r["step"] == "browser E2E" and r["status"] == "PASSED" for r in final["results"])
    lines.append("- " + ("Real" if e2e_passed else "Browser E2E, real") + " model quality and anything not listed above as PASSED were not verified by this run.")
    lines += ["", f"Tokens (as reported by the provider): in {d['usage']['input_tokens']}, out {d['usage']['output_tokens']}"]
    agent = [s["text"] for s in d["agent_summaries"] if not s.get("fix")]
    if agent:
        lines += ["", "## Agent's own summary (unverified claims)"] + [f"- {t}" for t in agent]
    return "\n".join(lines) + "\n"


def write(ledger) -> str:
    text = build(ledger)
    fsutil.atomic_write(ledger.dir / "report.md", text.encode("utf-8"))
    return text
