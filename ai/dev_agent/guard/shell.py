"""Shell guard for the `shell` tool. One command line may chain commands (`&&`, `||`, `;`, `|`) and redirect output. The line is split into its commands and each
one goes through the same `classify` as every other command, so: git writes, nested shells (bash -c, cmd, powershell) and the project's deny list are DENIED
(never approvable); destructive/system commands, installs, network, paths outside the project and unlisted commands ASK (as the Settings > Behavior switches
say); a redirect into a file is checked like a file write (forbidden/internal = denied, protected/outside the project = ask). Pure functions."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ai.dev_agent.guard import ALLOW, Decision, ask, deny
from ai.dev_agent.guard.commands import CommandError, classify, exe_name, split_command

SEPARATORS = ("&&", "||", ";", "|", "&")
SAFE = {"ls", "dir", "cat", "type", "head", "tail", "wc", "pwd", "echo", "where", "which", "uniq", "tree", "date", "cd", "true", "false", "diff", "fc", "findstr",
        "more", "hostname", "basename", "dirname", "realpath", "stat", "file", "cut", "tr", "nl", "md5sum", "sha256sum", "printenv", "grep", "egrep", "fgrep", "rg", "find"}
NULL_TARGETS = {"nul", "/dev/null", "&1", "&2", "1", "2"}


@dataclass
class Parsed:
    commands: list[list[str]] = field(default_factory=list)
    redirects: list[str] = field(default_factory=list)   # file targets of > and >>
    notes: list[str] = field(default_factory=list)       # things that make the line ask (substitution, input redirect ...)


def _scan(line: str, windows: bool) -> list[str]:
    """Split into tokens and separator tokens, honouring quotes. Raises CommandError on an unterminated quote."""
    tokens, buf, quote, i = [], "", "", 0
    started = False
    while i < len(line):
        ch = line[i]
        if quote:
            buf += ch
            if ch == quote:
                quote = ""
            elif ch == "\\" and quote == '"' and not windows and i + 1 < len(line):
                i += 1
                buf += line[i]
            i += 1
            continue
        if ch in "\"'":
            quote, buf, started = ch, buf + ch, True
        elif ch.isspace():
            if started:
                tokens.append(buf)
                buf, started = "", False
        elif line.startswith(SEPARATORS[:2], i) and line[i:i + 2] in ("&&", "||") or ch in ";|&":
            two = line[i:i + 2]
            sep = two if two in ("&&", "||") else ch
            if sep == "&" and buf.endswith((">", "<")):   # 2>&1
                buf, started = buf + ch, True
                i += 1
                continue
            if started:
                tokens.append(buf)
                buf, started = "", False
            tokens.append(sep)
            i += len(sep)
            continue
        elif ch in "<>" :
            if started and not buf.isdigit():
                tokens.append(buf)
                buf, started = "", False
            two = line[i:i + 2]
            op = (buf if buf.isdigit() else "") + (">>" if two == ">>" else ch)
            buf, started = "", False
            tokens.append(op)
            i += 2 if two == ">>" else 1
            dup = re.match(r"&\d", line[i:])   # 2>&1: the target is a file descriptor, not a separator
            if dup:
                tokens.append(dup.group())
                i += 2
            continue
        else:
            buf, started = buf + ch, True
        i += 1
    if quote:
        raise CommandError("unterminated quote in the command")
    if started:
        tokens.append(buf)
    return tokens


def _unquote(tok: str) -> str:
    return tok[1:-1] if len(tok) > 1 and tok[0] == tok[-1] and tok[0] in "\"'" else tok


def parse(line: str, windows: bool | None = None) -> Parsed:
    windows = os.name == "nt" if windows is None else windows
    if any(c in line for c in "\n\r\0"):
        raise CommandError("one single-line command per call (chain with &&)")
    out, current, i = Parsed(), [], 0
    tokens = _scan(line, windows)
    while i < len(tokens):
        tok = tokens[i]
        if tok in SEPARATORS:
            if current:
                out.commands.append(current)
            current = []
        elif re.fullmatch(r"\d?>>?", tok):
            target = _unquote(tokens[i + 1]) if i + 1 < len(tokens) else ""
            i += 1
            if re.fullmatch(r"&\d|\d", target) or target.lower() in NULL_TARGETS:
                pass
            elif target:
                out.redirects.append(target)
            else:
                out.notes.append("a redirect without a target")
        elif re.fullmatch(r"\d?<<?", tok):
            out.notes.append("input redirect or here-document")
            i += 1
        else:
            current.append(_unquote(tok) if windows else tok)
        i += 1
    if current:
        out.commands.append(current)
    if not windows:
        out.commands = [[_strip(t) for t in c] for c in out.commands]
    if re.search(r"\$\(|`|\$\{", line):
        out.notes.append("command substitution or variable expansion")
    if windows and re.search(r"[%^]", line):
        out.notes.append("cmd.exe variable expansion or escape characters (% ^)")
    return out


def _strip(tok: str) -> str:
    try:
        return split_command(tok, windows=False)[0] if tok else tok
    except CommandError:
        return tok


def _redirect(project, target: str, settings: dict) -> Decision:
    from ai.dev_agent.guard import paths
    try:
        rel, _ = project.resolve(target)
    except Exception:   # PathError: absolute path, '..', drive letter, reserved name
        return ask(f"output redirected to '{target}', a path outside the project")
    decision = paths.check_write(project, rel, "edit", None, {**settings, "ask_outside_plan": False})
    if decision.action == "deny" and decision.reason.startswith("no approved plan"):
        protected = project.protected_reason(rel)
        reason = project.forbidden_reason(rel) or project.secret_reason(rel)
        if reason:
            return deny(f"output redirected into {rel}: {reason}")
        if protected and settings.get("ask_protected_files", True):
            return ask(f"output redirected into {rel}: PROTECTED ({protected})")
        return ask(f"output redirected into the file {rel}: use write_file so the change is tracked")
    return decision


def classify_line(line: str, project, settings: dict | None = None, windows: bool | None = None) -> Decision:
    """allow | ask | deny for a whole command line."""
    settings = settings or {}
    try:
        parsed = parse(line, windows)
    except CommandError as exc:
        return deny(str(exc))
    if not parsed.commands:
        return deny("empty command")
    asks: list[str] = []
    unlisted = True
    for argv in parsed.commands:
        name = exe_name(argv[0])
        decision = ALLOW if name in SAFE and not any(a in ("-delete", "-exec", "-execdir", "-fprint", "--output") for a in argv[1:]) and classify_safe_paths(argv, project) else classify(
            [name, *argv[1:]] if name == "python" else argv, project.root, project.config["commands"])
        if decision.action == "deny":
            return decision
        if decision.action == "ask":
            asks.append(decision.reason)
            unlisted = unlisted and decision.kind == "unlisted"
    if settings.get("ask_protected_files", True):
        for argv in parsed.commands:
            for tok in argv[1:]:
                try:
                    rel, _ = project.resolve(tok.split("=", 1)[-1])
                except Exception:   # not a path inside the project
                    continue
                if project.protected_reason(rel):
                    asks.append(f"the command names the PROTECTED file {rel} ({project.protected_reason(rel)})")
                    unlisted = False
    for target in parsed.redirects:
        decision = _redirect(project, target, settings)
        if decision.action == "deny":
            return decision
        if decision.action == "ask":
            asks.append(decision.reason)
            unlisted = False
    asks += parsed.notes
    unlisted = unlisted and not parsed.notes
    if not asks:
        return ALLOW
    if unlisted and not settings.get("ask_other_commands", True):
        return ALLOW   # the owner switched the approval off: harmless commands that are only missing from the allow list run
    return Decision("ask", "; ".join(dict.fromkeys(asks)), "unlisted" if unlisted else "")


def classify_safe_paths(argv: list[str], project) -> bool:
    """A harmless read-only command still asks when it points outside the project (e.g. `cat C:\\Windows\\...`)."""
    from ai.dev_agent.guard.commands import _path_escape
    return not _path_escape(argv[1:], Path(project.root))
