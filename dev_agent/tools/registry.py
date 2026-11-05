"""Tool registry. A tool is `fn(ctx, args) -> dict`; errors come back as {"error": ...} so the model can react, they never crash the run."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.project import PathError


class ToolError(ValueError):
    pass


@dataclass
class Tool:
    name: str
    fn: object
    doc: str
    mutating: bool


REGISTRY: dict[str, Tool] = {}


def tool(name: str, doc: str, mutating: bool = False):
    def deco(fn):
        REGISTRY[name] = Tool(name, fn, doc, mutating)
        return fn
    return deco


def specs(readonly: bool) -> str:
    return "\n".join(f"- {t.name}: {t.doc}" for t in REGISTRY.values() if not (readonly and t.mutating))


def call(ctx, name: str, args) -> dict:
    found = REGISTRY.get(name)
    if not found:
        return {"error": f"unknown tool '{name}'. Available: {', '.join(REGISTRY)}"}
    if found.mutating and ctx.readonly:
        return {"error": f"{name} is not available while planning (read-only phase)"}
    if not isinstance(args, dict):
        return {"error": "args must be a JSON object"}
    try:
        return found.fn(ctx, args)
    except (ToolError, PathError) as exc:
        return {"error": str(exc)}
    except UnicodeDecodeError:
        return {"error": "binary or non-UTF-8 file: not editable as text"}
    except Exception as exc:   # a tool bug is reported to the model and the ledger, not raised
        return {"error": f"{type(exc).__name__}: {exc}"}
