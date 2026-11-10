"""Coding-agent foundation (phases 1-2): repo index, relevant-context picker, change plan check, safety flags, verification, memory.
Plain Python with no model calls: the same code serves the sysadmin's Agent tools and the command-line scripts used with VS Code."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def _agent_dir() -> Path:
    """coding_agent/ lives outside the package, next to it (override: settings.AI_AGENT_DIR)."""
    try:
        from django.conf import settings
        custom = getattr(settings, "AI_AGENT_DIR", None)
    except Exception:  # Django not configured (command-line agent scripts)
        custom = None
    return Path(custom) if custom else ROOT / "coding_agent"


AGENT_DIR = _agent_dir()
