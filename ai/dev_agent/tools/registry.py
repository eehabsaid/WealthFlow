"""Tool registry (MCP-style): a tool is a name, a description, a JSON schema for its arguments and a function `fn(ctx, args) -> dict`.
The loop never knows individual tools; it asks the registry for the specs (native tool-calling schemas) and calls tools by name. Add a tool with the
`@tool(...)` decorator in any module, call `register(Tool(...))`, list the module in `tool_modules` of coding_agent/config.json, or drop a `.py` file into
`coding_agent/tools/` (see tools/plugins.py). Errors come back as {"error": ...} so the model can react; they never crash the run."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.dev_agent.core.project import PathError


class ToolError(ValueError):
    pass


OPEN_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": True}


def schema(props: dict | None = None, required: tuple | list = ()) -> dict:
    """JSON schema of an argument object. props: {name: "string" | "integer" | "boolean" | {full schema}} - a plain type name gets no description."""
    out = {name: ({"type": spec} if isinstance(spec, str) else spec) for name, spec in (props or {}).items()}
    return {"type": "object", "properties": out, "required": list(required)}


@dataclass
class Tool:
    name: str
    fn: object
    doc: str
    mutating: bool = False
    params: dict = field(default_factory=lambda: dict(OPEN_SCHEMA))
    phases: tuple = ("plan", "work")   # where it is offered; "plan" only = submit_plan, "work" only = hidden while planning
    check_required: bool = True        # the registry names a missing required argument; the older tools keep their own explicit messages


REGISTRY: dict[str, Tool] = {}


def register(item: Tool) -> Tool:
    REGISTRY[item.name] = item
    return item


def unregister(name: str) -> None:
    REGISTRY.pop(name, None)


def tool(name: str, doc: str, mutating: bool = False, params: dict | None = None, phases: tuple = ("plan", "work")):
    def deco(fn):
        register(Tool(name, fn, doc, mutating, params or dict(OPEN_SCHEMA), phases))
        return fn
    return deco


def visible(readonly: bool, hidden=()) -> list[Tool]:
    """The tools offered in a phase: planning (readonly) = the non-mutating ones marked for "plan"; working = every tool marked for "work". `hidden` = names to leave out."""
    phase = "plan" if readonly else "work"
    return [t for t in REGISTRY.values() if phase in t.phases and not (readonly and t.mutating) and t.name not in hidden]


def specs(readonly: bool, hidden=()) -> str:
    return "\n".join(f"- {t.name}: {t.doc}" for t in visible(readonly, hidden))


def native_specs(readonly: bool, hidden=()) -> list[dict]:
    """The tools in the provider-neutral form adapters turn into their own API: [{name, description, parameters}]."""
    return [{"name": t.name, "description": t.doc, "parameters": t.params} for t in visible(readonly, hidden)]


_TRUE, _FALSE = {"true", "yes", "1", "on"}, {"false", "no", "0", "off"}


def _fit(spec: dict, value):
    """Make a small mistake of a local model harmless (a number sent as text, "true" for a boolean); anything else (a wrong shape) is left for the tool to refuse explicitly."""
    kind = spec.get("type")
    if kind == "integer" and isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    if kind == "integer" and isinstance(value, float) and value.is_integer():
        return int(value)
    if kind == "boolean" and isinstance(value, str) and value.strip().lower() in _TRUE | _FALSE:
        return value.strip().lower() in _TRUE
    if kind == "string" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return value


def check_args(item: Tool, args: dict) -> tuple[dict, str]:
    """(args made to fit the schema, problem). The problem text names the missing/odd argument so the model fixes it in its next call."""
    props, required = item.params.get("properties") or {}, item.params.get("required") or []
    args = {k: (_fit(props[k], v) if k in props else v) for k, v in args.items()}
    missing = [k for k in required if args.get(k) is None] if item.check_required else []   # an empty value is the tool's own explicit error ("empty path"), a missing one is named here
    if missing:
        return args, f"missing required argument(s): {', '.join(missing)}. Arguments of {item.name}: " + ", ".join(f"{k} ({v.get('type', 'any')})" for k, v in props.items())
    return args, ""


def call(ctx, name: str, args) -> dict:
    hidden, readonly = getattr(ctx, "hidden", ()), getattr(ctx, "readonly", False)
    found = REGISTRY.get(name)
    if not found or name in hidden or ("plan" if readonly else "work") not in found.phases:
        return {"error": f"unknown tool '{name}'. Available: {', '.join(t.name for t in visible(readonly, hidden))}"}
    if found.mutating and readonly:
        return {"error": f"{name} is not available while planning (read-only phase)"}
    if not isinstance(args, dict):
        return {"error": "args must be a JSON object"}
    args, problem = check_args(found, args)
    if problem:
        return {"error": problem}
    try:
        return found.fn(ctx, args)
    except (ToolError, PathError) as exc:
        return {"error": str(exc)}
    except UnicodeDecodeError:
        return {"error": "binary or non-UTF-8 file: not editable as text"}
    except Exception as exc:   # a tool bug is reported to the model and the ledger, not raised
        return {"error": f"{type(exc).__name__}: {exc}"}
