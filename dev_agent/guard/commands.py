"""Command guard: classify a command (argv) as allow / ask / deny. Pure functions. Git is STRICTLY read-only: any subcommand outside the
read-only list is denied, whatever the options, and a deny can never be overridden by an approval."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from . import ALLOW, Decision, ask, deny

WINDOWS_EXT = (".exe", ".cmd", ".bat", ".com")
WRAPPERS = {"cmd", "powershell", "pwsh", "bash", "sh", "zsh", "dash", "fish", "wsl", "env", "xargs", "sudo", "su", "doas", "runas",
            "start", "call", "nohup", "eval", "exec", "busybox", "script", "osascript", "gh", "hub"}
DESTRUCTIVE = {"rm", "rmdir", "del", "erase", "rd", "rimraf", "format", "mkfs", "dd", "shred", "truncate", "mv", "move", "ren", "rename",
               "cp", "copy", "xcopy", "robocopy", "chmod", "chown", "icacls", "takeown", "kill", "taskkill", "reg", "regedit", "sc", "net",
               "shutdown", "reboot", "diskpart", "fsutil", "curl", "wget", "ssh", "scp", "ftp"}
INSTALLERS = {"pip", "pip3", "npm", "yarn", "pnpm", "conda", "winget", "choco", "scoop", "apt", "apt-get", "brew", "npx"}
OPERATORS = {"&&", "||", ";", "|", "&", ">", ">>", "<", "2>&1", "1>&2", "2>", "|&"}
PY_NAME = re.compile(r"^(python|pythonw|py)(\d+(\.\d+)*)?$")

GIT_READ = {"status", "diff", "log", "show", "blame", "ls-files", "ls-tree", "rev-parse", "describe", "shortlog", "cat-file", "grep",
            "rev-list", "name-rev", "diff-tree", "for-each-ref", "show-ref", "merge-base", "whatchanged"}
GIT_GLOBAL_OK = {"--no-pager", "-P", "--no-optional-locks"}
GIT_BAD_LONG = ("--output", "--ext-diff", "--open-files-in-pager", "--no-index", "--exec-path", "--upload-pack", "--receive-pack",
                "--config-env", "--git-dir", "--work-tree")
GIT_BAD_SHORT = ("-O", "-c", "-C")


class CommandError(ValueError):
    pass


def split_command(text: str, windows: bool | None = None) -> list[str]:
    """Split one command line into argv (no shell is ever involved). Windows keeps backslashes and strips surrounding quotes."""
    windows = os.name == "nt" if windows is None else windows
    if any(c in text for c in "\n\r\0"):
        raise CommandError("one single-line command per call")
    try:
        if windows:
            return [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in "\"'" else t for t in shlex.split(text, posix=False)]
        return shlex.split(text)
    except ValueError as exc:
        raise CommandError(f"cannot parse the command: {exc}") from exc


def exe_name(argv0: str) -> str:
    base = re.split(r"[\\/]", argv0.strip())[-1].lower()
    for ext in WINDOWS_EXT:
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    return "python" if PY_NAME.match(base) else base


def _git(argv: list[str]) -> Decision:
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i] not in GIT_GLOBAL_OK:
            return deny(f"git option '{argv[i]}' before the subcommand is blocked (git is strictly read-only)")
        i += 1
    if i >= len(argv):
        return deny("give git a read-only subcommand: " + ", ".join(sorted(GIT_READ)))
    sub = argv[i].lower()
    if sub not in GIT_READ:
        return deny(f"git {sub} is blocked: git is strictly read-only (allowed: {', '.join(sorted(GIT_READ))})")
    for tok in argv[i + 1:]:
        if tok == "--":
            break
        low = tok.lower()
        if any(low == f or low.startswith(f + "=") for f in GIT_BAD_LONG) or tok.startswith(GIT_BAD_SHORT):
            return deny(f"git option '{tok}' is blocked (it can write files or run programs)")
    return ALLOW


def _path_escape(tokens: list[str], root: Path | None) -> str:
    for tok in tokens:
        value = tok.split("=", 1)[1] if tok.startswith("--") and "=" in tok else tok
        if value.startswith("-") or not value:
            continue
        if "://" in value:
            return f"URL argument: {value}"
        absolute = value.startswith(("/", "~", "\\")) or re.match(r"^[A-Za-z]:", value)
        if absolute or ".." in re.split(r"[\\/]", value):
            if root is None:
                return f"path outside the project: {value}"
            if value.startswith("~"):
                return f"path outside the project: {value}"
            target = (Path(value) if absolute else root / value).resolve()
            if not target.is_relative_to(root):
                return f"path outside the project: {value}"
    return ""


def _prefix(argv: list[str], rules) -> bool:
    for rule in rules:
        rule = [str(t) for t in rule]
        if rule and argv[: len(rule)] == [exe_name(rule[0]), *rule[1:]]:
            return True
    return False


def classify(argv: list[str], root: Path | None = None, commands: dict | None = None) -> Decision:
    commands = commands or {}
    if not argv:
        return deny("empty command")
    if any(t in OPERATORS for t in argv):
        return deny("shell operators (&&, |, >, ;) are not supported: run one command per call")
    name = exe_name(argv[0])
    if name in WRAPPERS:
        return deny(f"'{name}' runs other commands outside the guard and is blocked")
    if name == "git":
        return _git(argv)
    if name.startswith("git-") or name in ("gitk", "git"):
        return deny("only plain read-only `git <subcommand>` is allowed")
    canon = [name, *argv[1:]]
    if _prefix(canon, commands.get("deny", [])):
        return deny("command is on the project's deny list")
    flagged = next((a for a in argv[1:] if a in commands.get("ask_args", [])), None)
    if flagged:
        return ask(f"option {flagged} can change files directly, bypassing the protected-file guard")
    escape = _path_escape(argv[1:], root)
    if escape:
        return ask(f"{escape}: outside the approved scope")
    if _prefix(canon, commands.get("allow", [])):
        return ALLOW
    if _prefix(canon, commands.get("ask", [])):
        return ask("the project asks for approval before this command")
    if name in DESTRUCTIVE:
        return ask(f"'{name}' can destroy or move files, change the system or use the network")
    if name in INSTALLERS or (name == "python" and argv[1:3] in (["-m", "pip"], ["-m", "ensurepip"])):
        return ask("this installs or changes packages")
    return ask("not on the command whitelist")
