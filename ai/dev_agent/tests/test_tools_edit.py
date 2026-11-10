"""Large tool-call payloads remain valid and reach files without content changes."""

import json
from types import SimpleNamespace

from ai.dev_agent.engine.cancel import CancelToken
from ai.dev_agent.engine.protocol import error_details, nudge_for, parse_reply
from ai.dev_agent.engine.session import run_phase
from ai.dev_agent.providers.base import Reply
from ai.dev_agent.tools import call


def test_large_edit_payload_preserves_unicode_quotes_slashes_and_newlines(ctx):
    line = '# Café — “quotes” and \\\\paths\n# second line: "double" and \'single\'\n'
    content = line * 300
    reply = json.dumps({"tool": "edit_files", "args": {"edits": [{"path": "app/new.py", "content": content}]}},
                       ensure_ascii=False)
    action = parse_reply(reply)
    assert action.kind == "tool"
    result = call(ctx, *action.payload)
    assert result["ok"]
    assert (ctx.project.root / "app/new.py").read_bytes() == content.encode("utf-8")


def test_malformed_large_tool_call_reports_absolute_error_position():
    text = ('Provider note\n{"tool":"edit_files","args":{"edits":[{"path":"x",'
            '"replacements":[{"old":"a","new":"b"}]}}')
    got = parse_reply(text)
    assert got.kind == "invalid"
    position = error_details(got)["json_error_char"]
    assert position == len(text) - 1 and text[position] == "}"
    assert f"char {position}" in nudge_for(got)


def test_unescaped_newline_is_not_repaired():
    text = '{"tool":"edit_files","args":{"edits":[{"path":"x","content":"first\nsecond"}]}}'
    got = parse_reply(text)
    assert got.kind == "invalid"
    assert error_details(got)["json_error_char"] is not None


def test_plain_prose_still_gets_plain_nudge():
    got = parse_reply("Sure, I will do it.")
    assert got.kind == "invalid"
    assert "Sure" in nudge_for(got)


def test_valid_curly_quotes_are_not_rewritten():
    content = "Text with “curly” and ‘single’ quotes."
    reply = json.dumps({"tool": "edit_files", "args": {"edits": [{"path": "app/new.py", "content": content}]}},
                       ensure_ascii=False)
    assert parse_reply(reply).payload[1]["edits"][0]["content"] == content


def test_retry_includes_diagnostic_and_does_not_repeat_large_payload():
    broken = '{"tool":"edit_files","args":{"edits":['

    class Replies:
        calls = []

        def complete(self, system, messages, cancel=None):
            self.calls.append([dict(message) for message in messages])
            text = broken if len(self.calls) == 1 else '{"final":"recovered"}'
            return Reply(text, finish_reason="stop")

    provider = Replies()
    ctx = SimpleNamespace(cancel=CancelToken(), settings={"context_window": 10000, "reserve_tokens": 2000},
                          ledger=None, attachments=None, emit=lambda event: None)
    result = run_phase(ctx, provider, "system", "task", {"final"}, 3, attach=False)
    retry = provider.calls[1][-1]["content"]
    assert result.kind == "final" and "recovered" in result.payload
    assert f"char {len(broken)}" in retry
    assert "do not resend a large file payload" in retry
