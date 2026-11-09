"""Command tools: run_command (whitelist, ask or deny), run_tests, git (strictly read-only), note_proposal."""

from __future__ import annotations

from ai.dev_agent.guard.commands import CommandError, classify, split_command
from ai.dev_agent.tools import runner
from ai.dev_agent.tools.registry import ToolError, tool


def execute(ctx, argv: list[str], reason: str = "") -> dict:
    """Classify, ask the owner when needed, run. A deny is final: no approval can override it."""
    decision = classify(argv, ctx.project.root, ctx.project.config["commands"])
    shown = " ".join(argv)
    if decision.action == "deny":
        raise ToolError(f"blocked: {decision.reason}")
    if decision.action == "ask":
        why = f"{reason or 'no reason given'} | {decision.reason}"
        if not ctx.ask("command", f"cmd:{shown}", f"run `{shown}` ({why})"):
            raise ToolError(f"the owner did not approve `{shown}` ({decision.reason}); find another way or report it")
    result = runner.run(argv, ctx.project.root, ctx.settings["command_timeout_s"], ctx.settings["max_tool_result_chars"], cancel=ctx.cancel)
    ctx.emit({"type": "command", "command": shown[:300], "status": result["status"], "duration_s": result["duration_s"]})
    return {"command": shown, **result}


@tool("run_command", "args {command, reason}: run ONE command (no shell, no && | >). Whitelisted commands run; others need the owner's approval, so give a reason. "
      "git writes are blocked.", mutating=True)
def run_command(ctx, args):
    try:
        argv = split_command(str(args.get("command") or ""))
    except CommandError as exc:
        raise ToolError(str(exc)) from exc
    return execute(ctx, argv, str(args.get("reason") or ""))


@tool("git", "args {args:[...]}: read-only git (status, diff, log, show, blame, ls-files, rev-parse, ...). Anything that changes the repository is blocked.")
def git(ctx, args):
    parts = args.get("args")
    if not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
        raise ToolError("`args` must be a list of strings, e.g. [\"diff\", \"--stat\"]")
    return execute(ctx, ["git", *parts])


@tool("run_tests", "args {files?, modules?}: run the project's tests for these changed files (or explicit test modules)", mutating=True)
def run_tests(ctx, args):
    modules = {str(m) for m in args.get("modules") or []}
    for raw in args.get("files") or []:
        rel, _ = ctx.project.resolve(raw)
        if ctx.project.test_module(rel):
            modules.add(ctx.project.test_module(rel))
    if not modules:
        raise ToolError("no test module found for those files; pass `modules` explicitly")
    template = ctx.project.config["test_command"]
    argv = [a for t in template for a in (sorted(modules) if t == "{modules}" else [t])]
    return execute(ctx, argv, "run tests")


@tool("note_proposal", "args {path, text}: record a proposed change you may NOT make yourself (protected file); it goes in the final report", mutating=True)
def note_proposal(ctx, args):
    rel, _ = ctx.project.resolve(args.get("path"))
    text = str(args.get("text") or "").strip()
    if not text:
        raise ToolError("give the proposal `text`")
    if ctx.ledger:
        ctx.ledger.add_proposal(rel, text[:2000])
    return {"ok": True, "recorded": rel}
