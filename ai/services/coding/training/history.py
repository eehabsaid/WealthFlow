"""Reading this repo's git history for the coding dataset: commits, their files and diffs, and a throw-away checkout to run a commit's tests in."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile

from ai.services.investigation import paths

from ai.services.coding import ROOT


def git(*args: str, cwd=None, timeout: int = 120) -> str:
    done = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.decode("utf-8", "replace").strip()[:300])
    return done.stdout.decode("utf-8", "replace")


def commits(limit: int = 0) -> list[dict]:
    """Non-merge commits, oldest first: sha, parent, subject, body."""
    sep = "\x1e"
    out = git("log", "--no-merges", "--reverse", f"--format=%H{sep}%P{sep}%s{sep}%b\x1f")
    rows = []
    for chunk in out.split("\x1f"):
        parts = chunk.strip("\n").split(sep)
        if len(parts) == 4 and parts[0].strip():
            rows.append({"sha": parts[0].strip(), "parent": parts[1].split()[0] if parts[1].split() else "", "subject": parts[2].strip(), "body": parts[3].strip()})
    return rows[-limit:] if limit else rows


def changed_files(sha: str) -> list[str]:
    return [f for f in git("show", "--name-only", "--format=", "--no-renames", sha).splitlines() if f.strip()]


def file_at(sha: str, path: str) -> str:
    try:
        return git("show", f"{sha}:{path}")
    except RuntimeError:
        return ""


def diff_of(parent: str, sha: str, files: list[str]) -> str:
    """The unified diff of `files` between two commits, with anything credential-like masked."""
    return paths.redact(git("diff", "--no-renames", parent, sha, "--", *files)) if files else ""


@contextlib.contextmanager
def checkout(sha: str):
    """A clean copy of the repo at `sha` in a temp folder (git worktree); removed afterwards. Yields its path."""
    base = tempfile.mkdtemp(prefix="wf_coding_")
    path = os.path.join(base, "repo")
    git("worktree", "add", "--detach", path, sha, timeout=600)
    try:
        yield path
    finally:
        with contextlib.suppress(Exception):
            git("worktree", "remove", "--force", path)
        shutil.rmtree(base, ignore_errors=True)
        with contextlib.suppress(Exception):
            git("worktree", "prune")


def apply_patch(repo: str, patch: str) -> tuple[bool, str]:
    """(applied, message). The patch is checked first, so a bad one changes nothing."""
    if not patch.strip():
        return False, "empty patch"
    data = (patch.rstrip("\n") + "\n").encode("utf-8")
    for cmd in (["apply", "--check", "-"], ["apply", "--whitespace=nowarn", "-"]):
        done = subprocess.run(["git", *cmd], cwd=repo, input=data, capture_output=True, timeout=60)
        if done.returncode != 0:
            return False, done.stderr.decode("utf-8", "replace").strip()[:200]
    return True, "applied"


def patch_files(patch: str) -> list[str]:
    """Paths a unified diff touches (from its `+++ b/` and `--- a/` lines)."""
    found = []
    for line in patch.splitlines():
        if line.startswith(("+++ ", "--- ")):
            name = line[4:].strip().split("\t")[0]
            if name != "/dev/null":
                found.append(name[2:] if name[:2] in ("a/", "b/") else name)
    return sorted(set(found))
