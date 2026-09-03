"""
Tool-schema conversion and the generate() completion call for GeminiProvider.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from core.services.ai.credential_encryption import redact_secrets


class GeminiRequestMixin:
    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        decls = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            fn = t.get("function", t)
            if isinstance(fn, dict):
                name = str(fn.get("name", "")).strip()
                desc = str(fn.get("description", "")).strip()
                params = fn.get("parameters") or {"type": "object", "properties": {}}
                if name:
                    decls.append({
                        "name": name,
                        "description": desc,
                        "parameters": params,
                    })
        if decls:
            return [{"functionDeclarations": decls}]
        return None

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from core.integrations import gemini_provider as _gemini_provider_pkg

        if not self.api_key:
            err = "Gemini API key is unconfigured or missing."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        model_name = str(kwargs.get("model") or self.model or "").strip()
        if not model_name:
            err = "Gemini model name is unconfigured."
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": err}

        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models/{model_name}:generateContent?key={encoded_key}"

        system_instruction = None
        contents: list[dict[str, Any]] = []

        for m in messages:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "user")).lower()
            content = str(m.get("content", "")).strip()
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                g_role = "model" if role == "assistant" else "user"
                contents.append({"role": g_role, "parts": [{"text": content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        g_tools = self._convert_tools(tools)
        if g_tools:
            payload["tools"] = g_tools

        secrets = [self.api_key]
        timeout = int(kwargs.get("timeout") or max(self.timeout, 120))
        data, status, err = _gemini_provider_pkg.make_json_http_request(
            url=url,
            method="POST",
            payload=payload,
            timeout=timeout,
            secrets=secrets,
        )

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": safe_err}

        if not isinstance(data, dict):
            return {"content": "", "tool_calls": None, "prompt_tokens": None, "completion_tokens": None, "error": "Invalid response format from Gemini API."}

        candidates = data.get("candidates", [])
        cand = candidates[0] if isinstance(candidates, list) and candidates else {}
        parts = cand.get("content", {}).get("parts", []) if isinstance(cand, dict) else []

        text_parts = []
        tool_calls = []

        if isinstance(parts, list):
            for p in parts:
                if not isinstance(p, dict):
                    continue
                if "text" in p:
                    text_parts.append(str(p["text"]).strip())
                elif "functionCall" in p:
                    fc = p["functionCall"]
                    if isinstance(fc, dict):
                        tool_calls.append({
                            "function": {
                                "name": fc.get("name"),
                                "arguments": fc.get("args", {}),
                            }
                        })

        content_res = "\n".join(text_parts).strip()
        usage = data.get("usageMetadata") or {}
        prompt_tokens = usage.get("promptTokenCount") if isinstance(usage, dict) else None
        completion_tokens = usage.get("candidatesTokenCount") if isinstance(usage, dict) else None

        return {
            "content": content_res,
            "tool_calls": tool_calls if tool_calls else None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
        }
