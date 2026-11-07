"""Verify the changed files; when a check fails, give the model the clipped failure and let it fix it. Stops after 3 failed fix attempts on the
same error (or too many rounds overall) and leaves the exact state in the ledger."""

from __future__ import annotations

from . import verify
from .protocol import system_prompt
from .retries import RetryTracker, signature
from .session import run_phase


def verify_and_fix(ctx, provider, label: str, files_fn) -> tuple[bool, str]:
    """(ok, stop_reason). ok means no check FAILED; NOT RUN steps are kept in the ledger and reported, never hidden."""
    tracker, rounds, limit = RetryTracker(), 0, ctx.settings["max_fix_rounds"]
    while True:
        if ctx.cancel.is_set():
            return False, ctx.cancel.reason
        results = verify.run(ctx, files_fn())
        ctx.ledger.add_verification(label, results)
        ctx.emit({"type": "verify", "label": label, "overall": verify.overall(results), "results": [{"step": r["step"], "status": r["status"]} for r in results]})
        if ctx.cancel.is_set():
            return False, ctx.cancel.reason
        failed = [r for r in results if r["status"] == "FAILED"]
        if not failed:
            tracker.success()
            return True, ""
        sig = signature(failed[0]["detail"])
        if tracker.failure(sig):
            return False, f"3 fix attempts did not remove the same error: {sig}"
        rounds += 1
        if rounds > limit:
            return False, f"stopped after {limit} fix rounds without all checks passing"
        report = "\n\n".join(f"CHECK FAILED: {r['step']}\n{r['detail']}" for r in failed[:3])
        task = (f"{ctx.ledger.brief(ctx.package)}\n\nThe automatic checks on your changes FAILED (fix attempt {tracker.failed_fixes + 1} of 3 for this error).\n{report}\n\n"
                "Fix the cause with tools, then reply {\"final\": ...} saying what you changed. Do not weaken or delete tests to make them pass.")
        res = run_phase(ctx, provider, system_prompt(False), task, {"final"}, ctx.settings["max_steps_per_package"])
        if res.kind == "stopped":
            return False, res.reason
        ctx.ledger.data["agent_summaries"].append({"package": ctx.package, "fix": True, "text": str(res.payload)[:500]})
