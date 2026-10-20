"""How the loop writes a tool round into the conversation.

native (the provider says it accepts them, see BaseAIProvider.native_tool_messages): the assistant message carries the structured
`tool_calls` and every result comes back as a role "tool" message with the tool's name, exactly what the model was trained on.
text (every other provider): the call is an assistant sentence and the result a role "system" message "TOOL RESULT ...", so a
provider that forwards messages unchanged (OpenAI-style APIs need tool_call ids we do not have) keeps working."""

from __future__ import annotations

import json

TRIMMED = "[older result trimmed to save context]"


def calls_message(calls: list, native: bool) -> dict:
    if native:
        return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": n, "arguments": dict(a)}} for n, a in calls]}
    return {"role": "assistant", "content": "Calling " + "; ".join(f"{n}({json.dumps(a, default=str, ensure_ascii=False)[:160]})" for n, a in calls)}


def result_message(native: bool, name: str, args: dict, text: str) -> dict:
    if native:
        return {"role": "tool", "tool_name": name, "content": text}
    return {"role": "system", "content": f"TOOL RESULT ({name} {json.dumps(args, default=str, ensure_ascii=False)[:140]}):\n{text}"}


def notice_message(native: bool, name: str, text: str) -> dict:
    """A call that was not executed (repeated, over the read limit): the model still gets an answer for that call."""
    if native:
        return {"role": "tool", "tool_name": name, "content": text}
    return {"role": "system", "content": f"TOOL RESULT ({name}): {text}"}


def is_result(message: dict) -> bool:
    return message.get("role") == "tool" or (message.get("role") == "system" and str(message.get("content", "")).startswith("TOOL RESULT"))


def trimmed(message: dict) -> dict:
    """The same result message with its text replaced by a short note (the head line of a text-protocol result is kept)."""
    if message.get("role") == "tool":
        return {**message, "content": TRIMMED}
    return {**message, "content": f"{str(message['content']).split(chr(10), 1)[0]}\n{TRIMMED}"}
