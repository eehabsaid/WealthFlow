"""Command-line scanning and parsing for the shell guard."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from ai.dev_agent.guard.commands import CommandError, split_command


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
