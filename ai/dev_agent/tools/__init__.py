"""Importing this package registers every built-in tool (more come from tools/plugins.py)."""

from ai.dev_agent.tools import commands, edit, files, fs, notes, planning, readers, schemas, shell, web
from ai.dev_agent.tools.context import DenyAll, ToolContext
from ai.dev_agent.tools.registry import REGISTRY, Tool, call, native_specs, register, specs, tool

schemas.apply()

__all__ = ["commands", "edit", "files", "fs", "notes", "planning", "readers", "shell", "web", "DenyAll", "ToolContext", "REGISTRY", "Tool", "call", "native_specs", "register", "specs", "tool"]
