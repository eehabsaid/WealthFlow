"""The four provider adapters: the request they build for native tools and the tool calls they read back (no network: the HTTP post is replaced)."""

import pytest

from ai.dev_agent.providers import adapters
from ai.dev_agent.providers.base import MalformedOutput, NoToolSupport, ProviderError
from ai.dev_agent.providers.toolmsg import decode_args, to_text

TOOLS = [{"name": "read_file", "description": "read", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}]
HISTORY = [{"role": "user", "content": "task"},
           {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "read_file", "args": {"path": "a.py"}}, {"id": "c2", "name": "read_file", "args": {"path": "b.py"}}]},
           {"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": "A"}, {"role": "tool", "tool_call_id": "c2", "name": "read_file", "content": "B"},
           {"role": "user", "content": "go on"}]


def fake_post(monkeypatch, reply):
    sent = {}

    def post(url, headers, body, timeout, secrets=(), backoff=1.0, cancel=None):
        sent.update(url=url, body=body)
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(adapters, "post_json", post)
    return sent


def make(cls):
    return cls("m", "http://x", "key")


def test_ollama_sends_tools_without_json_format_and_reads_tool_calls(monkeypatch):
    sent = fake_post(monkeypatch, {"message": {"content": "", "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "a.py"}}}]}, "prompt_eval_count": 3, "eval_count": 2})
    reply = make(adapters.Ollama).complete("sys", HISTORY, tools=TOOLS)
    body = sent["body"]
    assert "format" not in body and body["tools"][0]["function"]["name"] == "read_file"
    assert body["messages"][2]["tool_calls"][0]["function"]["arguments"] == {"path": "a.py"} and body["messages"][3] == {"role": "tool", "tool_name": "read_file", "content": "A"}
    assert reply.tool_calls[0]["name"] == "read_file" and reply.tool_calls[0]["args"] == {"path": "a.py"} and reply.usage == {"input_tokens": 3, "output_tokens": 2}


def test_ollama_without_tools_keeps_the_json_format_and_sends_tool_messages_as_text(monkeypatch):
    sent = fake_post(monkeypatch, {"message": {"content": '{"final": "x"}'}})
    reply = make(adapters.Ollama).complete("sys", HISTORY)
    assert sent["body"]["format"] == "json" and "tools" not in sent["body"] and reply.tool_calls == [] and reply.text == '{"final": "x"}'
    assert all(m["role"] in ("system", "user", "assistant") for m in sent["body"]["messages"])


def test_ollama_errors_become_the_right_exception(monkeypatch):
    fake_post(monkeypatch, ProviderError("HTTP 400: registry.ollama.ai/x does not support tools"))
    with pytest.raises(NoToolSupport):
        make(adapters.Ollama).complete("s", HISTORY, tools=TOOLS)
    fake_post(monkeypatch, ProviderError("HTTP 500: error parsing tool call: raw='{bad'"))
    with pytest.raises(MalformedOutput):
        make(adapters.Ollama).complete("s", HISTORY, tools=TOOLS)
    fake_post(monkeypatch, ProviderError("HTTP 401"))
    with pytest.raises(ProviderError) as info:
        make(adapters.Ollama).complete("s", HISTORY, tools=TOOLS)
    assert not isinstance(info.value, (NoToolSupport, MalformedOutput))


def test_anthropic_groups_results_in_one_user_message(monkeypatch):
    sent = fake_post(monkeypatch, {"content": [{"type": "text", "text": "hm"}, {"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "z"}}], "usage": {"input_tokens": 1, "output_tokens": 1}})
    reply = make(adapters.Anthropic).complete("sys", HISTORY, tools=TOOLS)
    msgs = sent["body"]["messages"]
    assert sent["body"]["tools"][0]["input_schema"]["required"] == ["path"] and [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert [b["type"] for b in msgs[2]["content"]] == ["tool_result", "tool_result", "text"] and msgs[1]["content"][0]["type"] == "tool_use"
    assert reply.text == "hm" and reply.tool_calls == [{"id": "t1", "name": "read_file", "args": {"path": "z"}}]


def test_openai_tool_messages_and_arguments_as_json_text(monkeypatch):
    sent = fake_post(monkeypatch, {"choices": [{"message": {"content": None, "tool_calls": [{"id": "o1", "function": {"name": "read_file", "arguments": '{"path": "q"}'}}]}, "finish_reason": "tool_calls"}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    reply = make(adapters.OpenAI).complete("sys", HISTORY, tools=TOOLS)
    msgs = sent["body"]["messages"]
    assert msgs[2]["tool_calls"][0]["function"]["arguments"] == '{"path": "a.py"}' and msgs[3] == {"role": "tool", "tool_call_id": "c1", "content": "A"}
    assert reply.tool_calls[0]["args"] == {"path": "q"}


def test_openai_arguments_that_are_not_json_are_a_malformed_output(monkeypatch):
    fake_post(monkeypatch, {"choices": [{"message": {"content": "", "tool_calls": [{"id": "o1", "function": {"name": "read_file", "arguments": '{"path": '}}]}}], "usage": {}})
    with pytest.raises(MalformedOutput, match="read_file"):
        make(adapters.OpenAI).complete("sys", HISTORY, tools=TOOLS)


def test_gemini_function_parts_and_schema_subset(monkeypatch):
    sent = fake_post(monkeypatch, {"candidates": [{"content": {"parts": [{"functionCall": {"name": "read_file", "args": {"path": "g"}}}]}, "finishReason": "STOP"}], "usageMetadata": {}})
    reply = make(adapters.Gemini).complete("sys", HISTORY, tools=TOOLS)
    body = sent["body"]
    assert "additionalProperties" not in body["tools"][0]["functionDeclarations"][0]["parameters"]
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user", "user"] and len(body["contents"][2]["parts"]) == 2
    assert reply.tool_calls[0]["name"] == "read_file" and reply.tool_calls[0]["args"] == {"path": "g"}


def test_decode_args_and_text_conversion():
    assert decode_args("t", None) == {} and decode_args("t", '{"a": 1}') == {"a": 1}
    for bad in ('{"a"', "[1]", 3):
        with pytest.raises(MalformedOutput):
            decode_args("t", bad)
    text = to_text(HISTORY)
    assert text[1] == {"role": "assistant", "content": '{"tool": "read_file", "args": {"path": "a.py"}}'} and text[2]["content"].startswith("TOOL RESULT read_file:")
