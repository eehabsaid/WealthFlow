"""Which files a message asks for: the word patterns read a list and a bare "html"; the model reads follow-ups; nothing needs exact wording."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services.exports import intent, intent_model
from ai.views.ai_chat.chat_pipeline.document_request import wants_written_document

LIST = "generate a full user guide for the entire app as word, pdf, and html in well formatted Arabic"
FOLLOW_UP = "where is HTML file? don't think again only export the HTML file"
COMPLAINT = "why you don't generated the required HTML?"
HISTORY = [{"role": "user", "content": LIST}, {"role": "assistant", "content": "Here are your Word and PDF files."}]


def keys(text):
    return sorted(f.key for f in intent.detect(text))


class Provider:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def generate(self, messages, **kwargs):
        self.calls.append(messages)
        return {"content": self.replies.pop(0) if self.replies else "SAME"}


class Conversation:
    def __init__(self, rows):
        self.rows = rows

    @property
    def messages(self):
        return self

    def filter(self, **kwargs):
        return self

    def exclude(self, **kwargs):
        return self

    def order_by(self, *args):
        return [SimpleNamespace(role=m["role"], content=m["content"]) for m in reversed(self.rows)]


class WordPatternTest(SimpleTestCase):
    def setUp(self):
        intent.clear_resolved()

    def test_html_in_a_list_of_formats_is_found(self):
        self.assertEqual(keys(LIST), ["docx", "html", "pdf"])

    def test_a_bare_html_question_is_not_a_file_request(self):
        self.assertEqual(keys("what is html?"), [])

    def test_the_gate_skips_plain_data_questions(self):
        self.assertFalse(intent.might_want_file("how much do I owe on my loans"))
        self.assertFalse(intent.might_want_file("which file defines ExpenseService?"))
        self.assertTrue(intent.might_want_file(COMPLAINT))
        self.assertTrue(intent.might_want_file(FOLLOW_UP))

    def test_a_plain_file_word_counts_after_an_earlier_file_request(self):
        self.assertTrue(intent.might_want_file("where is the file you promised?", (LIST,)))
        self.assertFalse(intent.might_want_file("where is the file you promised?", ("how much do I owe?",)))


class ModelIntentTest(SimpleTestCase):
    def setUp(self):
        intent.clear_resolved()
        patcher = patch("ai.services.exports.settings.exports_enabled", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def resolve(self, text, *replies):
        provider = Provider(*replies)
        formats = intent_model.resolve_file_intent(provider, text, Conversation(HISTORY), SimpleNamespace(id=9))
        return sorted(f.key for f in formats), provider

    def test_a_follow_up_the_patterns_vetoed_is_understood(self):
        formats, _ = self.resolve(FOLLOW_UP, "html")
        self.assertEqual(formats, ["html"])
        self.assertTrue(wants_written_document(FOLLOW_UP))

    def test_a_complaint_with_no_command_is_understood(self):
        formats, _ = self.resolve(COMPLAINT, "html")
        self.assertEqual(formats, ["html"])

    def test_patterns_that_find_a_file_never_call_the_model(self):
        for text in ("export my loans to excel", LIST):
            formats, provider = self.resolve(text)
            self.assertTrue(formats)
            self.assertEqual(provider.calls, [])

    def test_none_and_unusable_replies_keep_the_patterns(self):
        for reply in ("none", "I think the user wants some files, maybe several of them", ""):
            self.assertEqual(self.resolve("how do I export my data to a file?", reply)[0], [])

    def test_no_file_word_means_no_model_call(self):
        formats, provider = self.resolve("how much do I owe on my loans")
        self.assertEqual((formats, provider.calls), ([], []))

    def test_a_provider_failure_never_raises(self):
        class Down:
            def generate(self, *a, **k):
                raise RuntimeError("offline")

        self.assertEqual(intent_model.resolve_file_intent(Down(), COMPLAINT, Conversation(HISTORY), SimpleNamespace(id=9)), [])

    def test_a_follow_up_is_restated_as_the_complete_request(self):
        formats = [f for f in intent_model.all_formats() if f.key == "html"]
        provider = Provider("Create the full user guide as an HTML file in well formatted Arabic")
        text = intent_model.restate_request(provider, FOLLOW_UP, Conversation(HISTORY), SimpleNamespace(id=9), formats)
        self.assertIn("Arabic", text)
        self.assertTrue(wants_written_document(text))

    def test_a_complete_message_is_kept_as_typed(self):
        formats = [f for f in intent_model.all_formats() if f.key == "html"]
        for reply in ("SAME", "", "two\n\nparagraphs"):
            self.assertEqual(intent_model.restate_request(Provider(reply), LIST, Conversation(HISTORY), SimpleNamespace(id=9), formats), LIST)
        self.assertEqual(intent_model.restate_request(Provider("x"), LIST, Conversation(HISTORY), SimpleNamespace(id=9), []), LIST)

    def test_parse(self):
        known = {"html", "pdf", "docx"}
        self.assertEqual(intent_model.parse("<think>x</think>HTML, pdf", known), ["html", "pdf"])
        self.assertEqual(intent_model.parse("NONE", known), [])
        self.assertIsNone(intent_model.parse("", known))
        self.assertIsNone(intent_model.parse("one two three four five six seven eight nine ten eleven twelve thirteen", known))
