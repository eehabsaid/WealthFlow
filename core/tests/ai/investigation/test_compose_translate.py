"""A guide asked for in another language: written in English (structure and coverage guaranteed), then translated chunk by chunk.
A translation is only accepted when complete (not cut off by the output limit, really in the target alphabet); a piece that cannot
be translated stays English so the guide never has a hole."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from core.services.ai.investigation.compose_sections import units
from core.services.ai.investigation.compose_translate import (acceptable, copied_share, latin_share, split_chunks,
                                                              target_language, translate_markdown)
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import make_user
from .test_compose_guide import GuideProvider, Result

ASK_AR = "write the user guide as a Word document in Arabic"
MARK = "ترجمة"


def arabic(markdown: str) -> str:
    """A fake translation: headings and sentences become Arabic words, Markdown structure kept."""
    out = []
    for line in markdown.splitlines():
        stripped = line.lstrip("#").strip()
        hashes = line[: len(line) - len(line.lstrip("#"))]
        out.append(f"{hashes} {MARK} {stripped.count(' ') + 1}".strip() if line.strip() and hashes else (f"{MARK} " * max(1, line.count(' ')) if line.strip() else line))
    return "\n".join(out)


class TranslatingProvider(GuideProvider):
    """Guide prompts as usual; language / alphabet questions answered; a translation call returns Arabic-looking text."""

    def __init__(self, language="Arabic", break_translation=False, cut_big_chunks=False, **kw):
        super().__init__(**kw)
        self.language, self.break_translation, self.cut_big_chunks = language, break_translation, cut_big_chunks

    def generate(self, messages, tools=None, **kwargs):
        system, ask = messages[0]["content"], messages[-1]["content"]
        if "the language the requested document must be written in" in system:
            self.calls.append({"system": system, "ask": ask})
            return {"content": self.language}
        if "Latin alphabet" in system:
            self.calls.append({"system": system, "ask": ask})
            return {"content": "NO" if self.language == "Arabic" else "YES"}
        if "professional translator" in system:
            self.calls.append({"system": system, "ask": ask, "max_tokens": kwargs.get("max_tokens")})
            if self.break_translation:
                return {"error": "model unavailable"}
            if self.cut_big_chunks and len(ask) > 900:     # a long chunk hits the output limit: the reply is a cut-off half
                return {"content": arabic(ask)[: len(ask) // 3], "completion_tokens": kwargs["max_tokens"]}
            return {"content": arabic(ask), "completion_tokens": 100}
        return super().generate(messages, tools, **kwargs)


class ChunkTest(SimpleTestCase):
    def test_chunks_cut_at_headings_and_join_back_to_the_original(self):
        md = "# Title\n\nintro\n\n" + "".join(f"## Screen {i}\n\n" + "".join(f"### Tab {j}\n\n{'word ' * 120}\n\n" for j in range(4)) for i in range(5))
        chunks = split_chunks(md, 2200)
        self.assertGreater(len(chunks), 5)
        self.assertTrue(all(len(c) <= 2200 for c in chunks))
        self.assertEqual("".join(chunks).replace("\n", ""), md.replace("\n", ""))

    def test_one_huge_paragraph_is_still_split(self):
        chunks = split_chunks("## A\n\n" + "\n".join("p" * 1000 for _ in range(9)), 2200)
        self.assertTrue(all(len(c) <= 3300 for c in chunks) and len(chunks) >= 4)

    def test_language_answers(self):
        ask = lambda answer: (lambda system, content, temperature=0: answer)  # noqa: E731
        self.assertEqual(target_language(ask("Arabic."), "x"), "Arabic")
        self.assertEqual(target_language(ask("English"), "x"), "")
        self.assertEqual(target_language(ask("x" * 600), "x"), "")
        self.assertEqual(target_language(ask(""), "x"), "")

    def test_what_counts_as_a_finished_translation(self):
        src = "## Screen\n\nOpen the menu and click Save to keep your changes in the application today.\n"
        ar = "## الشاشة\n\nافتح القائمة وانقر على حفظ للاحتفاظ بتغييراتك في التطبيق اليوم (Save).\n"
        self.assertTrue(acceptable(src, ar, cut=False, non_latin=True))
        self.assertFalse(acceptable(src, ar, cut=True, non_latin=True))                   # stopped by the output limit
        self.assertFalse(acceptable(src, src, cut=False, non_latin=False))                # unchanged
        self.assertFalse(acceptable(src, src.replace("Open", "Please open"), cut=False, non_latin=True))   # still English
        self.assertFalse(acceptable(src, "", cut=False, non_latin=True))
        self.assertFalse(acceptable(src, "ترجمة", cut=False, non_latin=True))             # far too short
        self.assertLess(latin_share(ar), 0.2)

    def test_a_piece_that_never_gets_translated_stays_english(self):
        md = "## Screen\n\nOpen the menu and click Save to keep your changes in the application today.\n"
        for reply in (md, "", "short"):
            got = translate_markdown(lambda s, c, t=0.1, r=reply: r, lambda: False, md, "Arabic", 10**12, None, True)
            self.assertEqual(got.strip(), md.strip())


class LanguageAgnosticChecksTest(SimpleTestCase):
    SRC = ("## Balance\n\nOpen the Balance page from the main menu and select the Bank Interest tab to record the interest that your "
           "bank paid you this month.\n\n1. Click the Add button and choose the bank account.\n2. Enter the amount and the date.\n")
    FRENCH = ("## Solde\n\nOuvrez la page Solde depuis le menu principal et sélectionnez l'onglet Intérêts bancaires (Bank Interest) "
              "pour enregistrer les intérêts que votre banque vous a versés ce mois-ci.\n\n1. Cliquez sur le bouton Ajouter (Add) "
              "et choisissez le compte bancaire.\n2. Saisissez le montant et la date.\n")

    def test_a_latin_alphabet_language_that_is_still_english_is_rejected(self):
        half = self.SRC.replace("Balance", "Solde").replace("Open the Solde page", "Ouvrez la page Solde")
        self.assertFalse(acceptable(self.SRC, half, cut=False, non_latin=False))
        self.assertGreater(copied_share(self.SRC, half), 0.6)

    def test_a_real_french_translation_is_accepted(self):
        self.assertTrue(acceptable(self.SRC, self.FRENCH, cut=False, non_latin=False))
        self.assertLess(copied_share(self.SRC, self.FRENCH), 0.3)

    def test_original_names_in_parentheses_do_not_make_arabic_look_english(self):
        src = "## Settings\n" + "".join(f"- Click the Setting Number {n} tab to open it now.\n" for n in range(6))
        ar = "## الإعدادات\n" + "".join(f"- انقر على علامة التبويب رقم {n} (Setting Number {n}) لفتحها.\n" for n in range(6))
        self.assertGreater(len(ar), 0.4 * len(src))
        self.assertTrue(acceptable(src, ar, cut=False, non_latin=True))

    def test_pieces_left_in_english_are_counted_and_logged(self):
        md = "## Screen\n\nOpen the menu and click Save to keep your changes in the application today.\n"
        stats = {}
        with self.assertLogs("core.services.ai.investigation.compose_translate", level="WARNING") as logs:
            translate_markdown(lambda s, c, t=0.1: "", lambda: False, md, "Arabic", 10**12, None, True, stats)
        self.assertEqual(stats, {"chunks": 1, "kept_english": 1})
        self.assertIn("stayed English", logs.output[0])


class TranslatedGuideTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("tr_admin", sysadmin=True)

    def run_guide(self, prov, ask=ASK_AR):
        prov.user = self.admin
        res = Result()
        self.assertTrue(ensure_document(prov, ask, res, 24000, self.admin, None))
        return res.content

    def test_the_guide_is_written_in_english_then_translated_and_covers_every_screen(self):
        prov = TranslatingProvider()
        doc = self.run_guide(prov)
        writing = [c for c in prov.calls if "Write ONLY" in c["ask"]]
        self.assertTrue(writing and all("Write the document in English" in c["ask"] for c in writing))
        self.assertIn(MARK, doc)
        self.assertNotIn("Open the screen from the menu", doc)               # no English paragraph left behind
        self.assertEqual(len([ln for ln in doc.splitlines() if ln.startswith("## ")]), len({u["page"] for u in units(self.admin)}))

    def test_every_translation_call_gets_the_document_output_limit(self):
        prov = TranslatingProvider()
        self.run_guide(prov)
        limits = {c["max_tokens"] for c in prov.calls if "professional translator" in c["system"]}
        self.assertEqual(limits, {1024})                                       # default context 4096 - 3500 reserved, floor 1024

    def test_a_translation_cut_off_by_the_output_limit_is_redone_in_smaller_pieces(self):
        prov = TranslatingProvider(cut_big_chunks=True)
        doc = self.run_guide(prov)
        translating = [c for c in prov.calls if "professional translator" in c["system"]]
        self.assertTrue(any(len(c["ask"]) <= 900 for c in translating))
        self.assertIn(MARK, doc)
        self.assertNotIn("Open the screen from the menu", doc)

    def test_english_requests_are_not_translated(self):
        prov = TranslatingProvider(language="English")
        doc = self.run_guide(prov, "write the user guide as a Word document")
        self.assertFalse([c for c in prov.calls if "professional translator" in c["system"]])
        self.assertTrue(doc.startswith("# WealthFlow user guide"))

    def test_when_translation_fails_the_english_guide_is_still_complete(self):
        doc = self.run_guide(TranslatingProvider(break_translation=True))
        for unit in units(self.admin):
            if unit["heading"]:                                            # a screen split in parts is ONE chapter
                self.assertIn(f"## {unit['heading']}", doc)
