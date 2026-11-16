"""Training-data redaction: secrets, emails, phone numbers and amounts with a currency are masked; plain numbers, dates, ids and file hashes survive.
The old phone rule masked any run of 9+ digits, which turned dates, ids and plain amounts in source code and tool output into ***REDACTED***."""

from django.test import SimpleTestCase

from ai.services.coding.training import ledger_examples as le

MASK = "***REDACTED***"
CFG = {"redact_patterns": True}
SHA = "ab12" * 16


class RedactPiiTests(SimpleTestCase):
    def test_plain_numbers_dates_ids_and_hashes_are_kept(self):
        for text in ("total = 1250.50", "id 1234567890", "stamp 20261113123045", "on 2026-11-13", "100 200 300 400", "x = 1,234,567 rows", f"sha {SHA}", "$12"):
            self.assertEqual(le.redact_pii(text, CFG), (text, 0), text)

    def test_real_pii_is_still_masked_and_counted(self):
        text = "mail a@b.com, call 555-123-4567 or +20 100 123 4567, it costs $42.50 or 5,000 EGP"
        out, hits = le.redact_pii(text, CFG)
        self.assertEqual(out, f"mail {MASK}, call {MASK} or {MASK}, it costs {MASK} or {MASK}")
        self.assertEqual(hits, 5)

    def test_the_old_bug_a_date_and_a_plain_amount_next_to_an_email(self):
        out, _ = le.redact_pii("2026-11-13 balance 1250.50 owner a@b.com", CFG)
        self.assertEqual(out, f"2026-11-13 balance 1250.50 owner {MASK}")

    def test_secrets_are_masked_even_when_the_pattern_pass_is_off(self):
        out, hits = le.redact_pii('mail a@b.com $1,200.00 token = "abcd1234efgh"', {"redact_patterns": False})
        self.assertEqual(out, f'mail a@b.com $1,200.00 token = "{MASK}"')
        self.assertEqual(hits, 0)

    def test_a_qa_example_keeps_the_plain_numbers_of_the_answer(self):
        example, why = le.qa_candidate({"id": "t1", "status": "answered", "goal": "what is the limit on 2026-11-13?", "answer": "The limit is 1250.50 (id 1234567890); mail a@b.com."},
                                       {"system_prompt": "s", "max_context_chars": 9999, "max_answer_chars": 9999})
        self.assertEqual(why, "")
        self.assertIn("1250.50 (id 1234567890)", example["answer"])
        self.assertIn("2026-11-13", example["goal"])
        self.assertNotIn("a@b.com", example["answer"])
        self.assertEqual(example["redactions"], 1)
