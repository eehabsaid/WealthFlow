"""A message with attached files that include a picture: while image generation is available the model may call
generate_image (edit the picture, or make a new one) once. The same tool, executor and permissions as the Agent path."""

from __future__ import annotations

import json
from typing import Any

from ai.services.image_generation import NOTICE, TOOL_DEF, image_generation_available
from ai.services.tools import validate_and_execute_tool
from ai.views.ai_chat.ai_chat_helpers import _parse_tool_call


def offered(provider: Any, attachments) -> bool:
    return bool(getattr(provider, "supports_tools", False)) and image_generation_available() and any(a.kind == "image" for a in attachments)


def system_note(attachments) -> str:
    pictures = ", ".join(f"id={a.id} ({a.name})" for a in attachments if a.kind == "image")
    return f" {NOTICE} Attached pictures you may edit with source_image_id: {pictures}."


def run(provider: Any, user: Any, messages: list[dict], result: dict) -> tuple[dict, list[dict]]:
    """(final model result, executed tool audit records). If the first reply called generate_image, run it and let the model answer."""
    calls = [_parse_tool_call(c) for c in (result.get("tool_calls") or [])]
    name, args = next(((n, a) for n, a in calls if n == TOOL_DEF["name"]), ("", {}))
    if not name:
        return result, []
    audit, outcome = validate_and_execute_tool(name, args, user)
    data = outcome.get("data") if outcome.get("ok") else {"error": outcome.get("error")}
    follow = [*messages, {"role": "system", "content": f"TOOL generate_image RESULT: {json.dumps(data, default=str)}\n"
                                                       "Answer the user in one or two sentences, in their language. Do not call the tool again."}]
    return provider.generate(follow), [audit]
