"""Message and schema converters for each provider API."""

from __future__ import annotations

from ai.dev_agent.providers.base import merge_roles


def _anthropic(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image", "source": {"type": "base64", "media_type": i["mime"], "data": i["data"]}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [*parts, {"type": "text", "text": m["content"]}]}


def _anthropic_all(messages):
    """Native tool messages: tool_use blocks in the assistant message; the results of one turn go back together in ONE user message."""
    out: list[dict] = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) and out[-1].get("_results"):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block], "_results": True})
        elif m.get("tool_calls"):
            blocks = ([{"type": "text", "text": m["content"]}] if m["content"] else []) + [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]} for c in m["tool_calls"]]
            out.append({"role": "assistant", "content": blocks})
        else:
            msg = _anthropic(m)
            if out and out[-1].get("_results") and msg["role"] == "user":   # text after tool results shares their user message
                out[-1]["content"].extend(msg["content"] if isinstance(msg["content"], list) else [{"type": "text", "text": msg["content"]}])
            else:
                out.append(msg)
    return [{k: v for k, v in m.items() if k != "_results"} for m in out]


def _ollama(m):
    return {"role": m["role"], "content": m["content"], **({"images": [i["data"] for i in m.get("images", ())]} if m.get("images") else {})}


def _ollama_all(messages):
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            out.append({"role": "tool", "tool_name": m.get("name", ""), "content": m["content"]})
        elif m.get("tool_calls"):
            out.append({"role": "assistant", "content": m["content"], "tool_calls": [{"function": {"name": c["name"], "arguments": c["args"]}} for c in m["tool_calls"]]})
        else:
            out.append(_ollama(m))
    return out


def _openai(m):
    if not m.get("images"):
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "image_url", "image_url": {"url": f"data:{i['mime']};base64,{i['data']}"}} for i in m.get("images", ())]
    return {"role": m["role"], "content": [{"type": "text", "text": m["content"]}, *parts]}


def _openai_all(messages):
    import json
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        elif m.get("tool_calls"):
            out.append({"role": "assistant", "content": m["content"] or None,
                        "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)}} for c in m["tool_calls"]]})
        else:
            out.append(_openai(m))
    return out


def _gemini(m):
    parts = [{"text": m["content"]}, *({"inline_data": {"mime_type": i["mime"], "data": i["data"]}} for i in m.get("images", ()))]
    return {"role": "model" if m["role"] == "assistant" else "user", "parts": parts}


def _gemini_all(messages):
    out = []
    for m in merge_roles(messages):
        if m["role"] == "tool":
            part = {"functionResponse": {"name": m.get("name", ""), "response": {"result": m["content"]}}}
            if out and out[-1].get("_results"):
                out[-1]["parts"].append(part)
            else:
                out.append({"role": "user", "parts": [part], "_results": True})
        elif m.get("tool_calls"):
            out.append({"role": "model", "parts": ([{"text": m["content"]}] if m["content"] else []) + [{"functionCall": {"name": c["name"], "args": c["args"]}} for c in m["tool_calls"]]})
        else:
            out.append(_gemini(m))
    return [{k: v for k, v in m.items() if k != "_results"} for m in out]


def _gemini_schema(schema):
    """Gemini accepts only a subset of JSON schema."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items() if k not in ("additionalProperties", "default", "minimum", "maximum", "minItems", "maxItems")}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema
