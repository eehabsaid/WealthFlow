"""
Tool-schema conversion and the generate() completion call for ClaudeProvider.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.credential_encryption import redact_secrets


class ClaudeRequestMixin:
    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        converted = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            fn = t.get("function", t)
            if isinstance(fn, dict):
                name = str(fn.get("name", "")).strip()
                desc = str(fn.get("description", "")).strip()
                params = fn.get("parameters") or {"type": "object", "properties": {}}
                if name:
                    converted.append({
                        "name": name,
                        "description": desc,
                        "input_schema": params,
                    })
        return converted or None

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from core.integrations import claude_provider as _claude_provider_pkg

        if not self.api_key:
            err = "Claude API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        model_name = str(kwargs.get("model") or self.model or "").strip()
        if not model_name:
            err = "Claude model name is unconfigured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        system_prompt = ""
        claude_msgs: list[dict[str, Any]] = []

        for m in messages:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "user")).lower()
            content = str(m.get("content", "")).strip()
            if role == "system":
                system_prompt = f"{system_prompt}\n{content}".strip() if system_prompt else content
            else:
                c_role = "assistant" if role == "assistant" else "user"
                claude_msgs.append({"role": c_role, "content": content})

        if not claude_msgs:
            claude_msgs.append({"role": "user", "content": "Hello"})

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": claude_msgs,
            "max_tokens": int(kwargs.get("max_tokens") or 2048),
        }
        if system_prompt:
            payload["system"] = system_prompt

        c_tools = self._convert_tools(tools)
        if c_tools:
            payload["tools"] = c_tools

        secrets = [self.api_key]
        timeout = int(kwargs.get("timeout") or max(self.timeout, 120))
        data, status, err = _claude_provider_pkg.make_json_http_request(
            url=url,
            method="POST",
            headers=headers,
            payload=payload,
            timeout=timeout,
            secrets=secrets,
        )

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from Anthropic API."}

        content_blocks = data.get("content", [])
        text_parts = []
        tool_calls = []

        if isinstance(content_blocks, list):
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                b_type = block.get("type")
                if b_type == "text":
                    text_parts.append(str(block.get("text", "")).strip())
                elif b_type == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "function": {
                            "name": block.get("name"),
                            "arguments": block.get("input", {}),
                        }
                    })

        content_res = "\n".join(text_parts).strip()
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
        completion_tokens = usage.get("output_tokens") if isinstance(usage, dict) else None

        return {
            "content": content_res,
            "tool_calls": tool_calls if tool_calls else None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
        }
