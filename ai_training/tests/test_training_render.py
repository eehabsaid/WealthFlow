"""Training text, markers and masks from the chat template (fake ChatML tokenizer; the real template is only on your PC)."""

from __future__ import annotations

import os
import tempfile

from django.test import SimpleTestCase

from ai_training.trainer import render

from .fakes import FakeTokenizer, messages, write_jsonl

TOOLS = [{"type": "function", "function": {"name": "app_data_query"}}]


def trained_spans(text: str, user_marker: str, assistant_marker: str) -> list[str]:
    """What train_on_responses_only keeps: the text after each assistant marker up to the next user marker."""
    spans = []
    for part in text.split(assistant_marker)[1:]:
        spans.append(part.split(user_marker)[0])
    return spans


class MarkerTest(SimpleTestCase):
    def test_markers_come_from_the_template_for_both_thinking_modes(self):
        for thinking in (True, False):
            self.assertEqual(render.find_markers(FakeTokenizer(), thinking), ("<|im_start|>user\n", "<|im_start|>assistant\n"))

    def test_a_template_without_clear_markers_is_refused(self):
        with self.assertRaises(ValueError):
            render.find_markers(FakeTokenizer(broken=True), False)

    def test_only_assistant_turns_are_trained(self):
        tok = FakeTokenizer()
        text = tok.apply_chat_template(messages(), tools=TOOLS, enable_thinking=False)
        users, assistant = render.find_markers(tok, False)
        spans = "".join(trained_spans(text, users, assistant))
        self.assertIn("<tool_call>app_data_query", spans)       # the investigation step is learned
        self.assertIn("You have 6 goal records.", spans)        # and the answer
        self.assertNotIn("SYSTEM RULES", spans)                 # not the system prompt
        self.assertNotIn("How many goal records", spans)        # not the question
        self.assertNotIn("<tool_response>", spans)              # not the tool results


class RenderFileTest(SimpleTestCase):
    def test_counts_kept_too_long_and_unreadable_lines(self):
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        long = messages(result="word " * 400)
        write_jsonl(path, [{"messages": messages(), "tools": TOOLS}, {"messages": long, "tools": TOOLS}, "not json", '{"nomessages": 1}', ""])
        texts, stats = render.render_file(path, FakeTokenizer(), 200, False)
        self.assertEqual((len(texts), stats["lines"], stats["kept"], stats["too_long"], stats["unreadable"]), (1, 4, 1, 1, 2))
        self.assertGreater(stats["max_tokens"], 400)

    def test_tools_and_tool_calls_are_rendered_by_the_template(self):
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        write_jsonl(path, [{"messages": messages(), "tools": TOOLS}])
        text = render.render_file(path, FakeTokenizer(), 1000, False)[0][0]
        self.assertIn("TOOLS", text)
        self.assertIn('<tool_call>app_data_query {"model": "Goal"}</tool_call>', text)

    def test_stats_file_is_written(self):
        folder = tempfile.mkdtemp()
        self.assertTrue(os.path.exists(render.write_stats({"kept": 1}, folder)))
