"""Coding-agent foundation (phases 1-2): repo index, relevant-context picker, change plan check, safety flags, verification, memory.
Plain Python with no model calls: the same code serves the sysadmin's Agent tools and the command-line scripts used with VS Code."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AGENT_DIR = ROOT / "coding_agent"
