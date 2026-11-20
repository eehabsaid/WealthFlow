"""Native tool messages. The loop keeps ONE message format:
  {"role": "assistant", "content": text, "tool_calls": [{"id", "name", "args"}]}   a reply that calls tools
  {"role": "tool", "tool_call_id", "name", "content"}                              one tool result
Adapters map it to their own API. `to_text` turns it into the plain-text JSON protocol (for models/servers without a tools API and for the scripted test models)."""

from __future__ import annotations

import itertools
import json

_ids = itertools.count(1)


def new_id() -> str:
    return f"call_{next(_ids)}"


def decode_args(name: str, raw):
    """Arguments of a native tool call -> dict. A JSON string is decoded; anything that is not an object is a MalformedOutput (the model is told)."""
    from ai.dev_agent.providers.base import MalformedOutput
    if raw in (None, ""):
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise MalformedOutput(f"the arguments of your call to {name} are not valid JSON ({exc}); send them again as one JSON object") from exc
    if not isinstance(raw, dict):
        raise MalformedOutput(f"the arguments of your call to {name} must be a JSON object, not {type(raw).__name__}")
    return raw


def to_text(messages: list[dict]) -> list[dict]:
    """Native -> text protocol: an assistant tool call becomes the JSON the old protocol used, a tool result becomes a `TOOL RESULT` user message."""
    out: list[dict] = []
    for m in messages:
        if m["role"] == "tool":
            out.append({"role": "user", "content": f"TOOL RESULT {m.get('name', '')}:\n{m['content']}"})
        elif m.get("tool_calls"):
            text = "\n".join(json.dumps({"tool": c["name"], "args": c["args"]}, ensure_ascii=False) for c in m["tool_calls"][:1])
            out.append({"role": "assistant", "content": text})
        else:
            out.append(m)
    return out
