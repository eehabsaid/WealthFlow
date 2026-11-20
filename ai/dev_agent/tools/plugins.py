"""Extra tools without touching the loop. Two sources, both owned by the repo owner (tasks cannot write coding_agent/):
  1. `tool_modules` in coding_agent/config.json: importable module names; importing one registers its `@tool` functions (or it defines `register_tools(registry)`).
  2. `coding_agent/tools/*.py`: each file is loaded the same way.
A broken plugin is reported in `errors` and skipped; it never stops the agent."""

from __future__ import annotations

import importlib
import importlib.util

from ai.dev_agent.tools import registry

_loaded: set[str] = set()


def _use(module) -> None:
    hook = getattr(module, "register_tools", None)
    if callable(hook):
        hook(registry)


def load(project) -> list[str]:
    """Load the project's tool plugins once per process and root; returns the problems found (empty = all fine)."""
    errors: list[str] = []
    for name in project.config.get("tool_modules") or []:
        key = f"module:{name}"
        if key in _loaded:
            continue
        try:
            _use(importlib.import_module(str(name)))
            _loaded.add(key)
        except Exception as exc:   # a plugin is foreign code: whatever it raises, the agent goes on
            errors.append(f"tool module {name}: {type(exc).__name__}: {exc}")
    folder = project.agent_dir / "tools"
    for path in sorted(folder.glob("*.py")) if folder.is_dir() else []:
        key = f"file:{path.resolve()}:{path.stat().st_mtime_ns}"
        if key in _loaded or path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"dev_agent_plugin_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _use(module)
            _loaded.add(key)
        except Exception as exc:
            errors.append(f"tool file {path.name}: {type(exc).__name__}: {exc}")
    return errors
