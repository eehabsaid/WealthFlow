"""Guide structure that must survive the evidence, the model and the translator: no copied documentation twice, no empty
headings, and the heading levels of the English source in the translation."""

from django.test import SimpleTestCase

from core.services.ai.investigation.compose_descriptions import _unique, page_evidence
from core.services.ai.investigation.compose_flatten import drop_empty_headings, tidy
from core.services.ai.investigation.compose_translate import restore_levels


def item(name, purpose, steps=("a",), labelled=True):
    return {"name": name, "purpose": purpose, "steps": list(steps), "_labelled": labelled}


class EvidenceTest(SimpleTestCase):
    def test_copies_of_the_tab_text_and_of_each_other_are_dropped_and_the_labelled_name_wins(self):
        parent = {"purpose": "Manage assets.", "steps": ["a"]}
        items = [item("Asset Core", "Gold.", labelled=False), item("Photos", "Photos."), item("Gold Details", "Gold."),
                 item("Vehicle", "Manage assets.")]
        self.assertEqual([i["name"] for i in _unique(items, parent)], ["Gold Details", "Photos"])

    def test_items_without_text_are_never_treated_as_copies(self):
        self.assertEqual(len(_unique([{"name": "A", "_labelled": True}, {"name": "B", "_labelled": True}], None)), 2)

    def test_the_live_fixed_assets_evidence_has_no_empty_or_copied_dialogs(self):
        names = [i["name"] for i in page_evidence("fixed-assets", ["assets"])["tabs"]["assets"]["items"]]
        self.assertIn("Gold Details", names)
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse({"Vehicle", "Maintenance", "Insurance", "Details", "Asset Core"} & set(names))


class HeadingsTest(SimpleTestCase):
    def test_empty_tab_and_dialog_headings_are_dropped_but_a_tab_with_dialogs_stays(self):
        text = "## Ch\n\nIntro.\n\n### Tab\n\n#### Dialog\n\nSteps.\n\n#### Empty\n\n#### Empty 2\n\n### Last\n"
        out = drop_empty_headings(text)
        self.assertEqual([x for x in out.splitlines() if x.startswith("#")], ["## Ch", "### Tab", "#### Dialog"])

    def test_translation_gets_the_source_heading_levels_when_the_counts_match(self):
        source = "## A\n\n### B\n\n#### C\n\ntext"
        self.assertEqual(restore_levels(source, "## ا\n\n### ب\n\n### ج\n\nنص"), "## ا\n\n### ب\n\n#### ج\n\nنص")

    def test_translation_is_left_alone_when_a_heading_was_lost(self):
        self.assertEqual(restore_levels("## A\n### B\n#### C", "## ا\n### ج"), "## ا\n### ج")

    def test_a_continuation_part_loses_its_own_introduction_but_the_first_part_keeps_its_text(self):
        text = "The Settings screen contains five tabs.\n\n### Roles\n\nBody.\n"
        self.assertEqual(tidy(text, {"tab_items": [{"name": "Roles"}], "part": (2, 3)}), "### Roles\n\nBody.")
        self.assertTrue(tidy(text, {"tab_items": [{"name": "Roles"}], "part": (1, 3)}).startswith("The Settings screen"))


class DocumentedStepsTest(SimpleTestCase):
    @staticmethod
    def _units():
        from unittest.mock import patch

        from core.services.ai.investigation.compose_sections import units

        class _Admin:
            is_authenticated = True

        with patch("core.authentication.utils.auth_utils.user_is_sysadmin", return_value=True):
            return list(units(_Admin()))

    def test_a_documented_tab_and_dialog_written_without_steps_get_the_documented_steps(self):
        from core.services.ai.investigation.compose_flatten import ensure_steps

        unit = next(u for u in self._units() if "Card Renewal Fee" in u["tabs"])
        section = "## Balance\n\n### Card Renewal Fee\n\nRecord the fees.\n\n#### Add Card Renewal Fee\n\nAdd a fee.\n\n### Allocation\n\n1. Open it.\n"
        out = ensure_steps(section, unit)
        self.assertIn("1. Open Balance > Card Renewal Fee.", out)
        self.assertIn("1. Click New Card Renewal Fee (or Edit on a row).", out)
        self.assertEqual(out.count("1. Open it."), 1)               # a section that has its list is not touched
        self.assertNotIn("Open Balance > Card Renewal Fee.\n\n\n", out)

    def test_every_documented_item_of_the_live_guide_ends_up_with_a_list(self):
        from core.services.ai.investigation.compose_flatten import _LIST_LINE, _documented_steps, ensure_steps

        for unit in self._units():
            names = _documented_steps(unit)
            section = "## T\n\n" + "\n\n".join(f"### {n.title()}\n\nOnly a purpose." for n in names)
            out = ensure_steps(section, unit)
            parts = out.split("### ")[1:]
            self.assertTrue(all(any(_LIST_LINE.match(x) for x in p.splitlines()) for p in parts), unit["title"])

    def test_the_expense_dialog_is_named_from_its_own_title_not_its_key(self):
        names = [i["name"] for i in page_evidence("expenses", [])["items"]]
        self.assertIn("Add or Edit Expense", names)
        self.assertNotIn("Edit Add Expenses", names)


class TranslationGuardsTest(SimpleTestCase):
    SOURCE = "### A\n\nPurpose one is here.\n\n1. Step.\n\n### B\n\nPurpose two is here.\n\n1. Step.\n\n### C\n\nPurpose three.\n\n1. Step.\n\n### D\n\nPurpose four.\n\n1. Step.\n"

    def test_a_translation_that_drops_purpose_sentences_is_rejected(self):
        from core.services.ai.investigation.compose_translate import rejection

        kept = "### أ\n\nالغرض الأول هنا.\n\n1. خطوة.\n\n### ب\n\nالغرض الثاني هنا.\n\n1. خطوة.\n\n### ج\n\nالغرض الثالث.\n\n1. خطوة.\n\n### د\n\nالغرض الرابع.\n\n1. خطوة.\n"
        dropped = "### أ\n\nالغرض الأول هنا.\n\n1. خطوة.\n\n### ب\n\n1. خطوة.\n\n### ج\n\n1. خطوة.\n\n### د\n\n1. خطوة.\n"
        self.assertEqual(rejection(self.SOURCE, kept, False, True), "")
        self.assertEqual(rejection(self.SOURCE, dropped, False, True), "paragraphs lost")

    def test_translated_headings_lose_a_trailing_english_name_but_steps_keep_theirs(self):
        from core.services.ai.investigation.compose_translate import clean_headings

        text = "### تبادل العملات (Currency Exchange)\n\n1. انقر على تبادل جديد (New Exchange).\n#### إضافة (Add Role)\n### Plain English (Heading)\n"
        out = clean_headings(text)
        self.assertEqual(out.splitlines()[0], "### تبادل العملات")
        self.assertIn("(New Exchange)", out)
        self.assertEqual(out.splitlines()[2], "#### إضافة")
        self.assertEqual(out.splitlines()[3], "### Plain English (Heading)")    # a heading with no translated text is left alone


class FinalStepsPassTest(SimpleTestCase):
    def test_the_finished_guide_gets_documented_steps_whatever_happened_before(self):
        from core.services.ai.investigation.compose_flatten import ensure_steps_document

        unit = next(u for u in DocumentedStepsTest._units() if "Card Renewal Fee" in u["tabs"])
        guide = f"# Guide\n\nIntro.\n\n## {unit['title']}\n\nChapter text.\n\n### Card Renewal Fee\n\nRecord fees.\n\n#### Add Card Renewal Fee\n\nAdd a fee.\n\n## Other\n\n### Card Renewal Fee\n\nNot this chapter.\n"
        out = ensure_steps_document(guide, [unit])
        self.assertIn("1. Open Balance > Card Renewal Fee.", out)
        self.assertIn("1. Click New Card Renewal Fee (or Edit on a row).", out)
        self.assertEqual(out.count("Open Balance > Card Renewal Fee."), 1)     # only in the chapter of that screen
        self.assertTrue(out.startswith("# Guide\n\nIntro."))


class DialogLevelTest(SimpleTestCase):
    def test_documented_dialogs_written_as_tabs_go_back_to_dialog_level(self):
        from core.services.ai.investigation.compose_flatten import tidy

        unit = next(u for u in DocumentedStepsTest._units() if "Assets" in u["tabs"] and u["title"] == "Fixed Assets")
        text = ("## Fixed Assets\n\nIntro.\n\n### Assets\n\nManage assets.\n\n1. Open.\n\n### General\n\nGeneral info.\n\n1. Open General.\n\n"
                "### Dashboard\n\nSummary.\n\n1. Open.\n")
        heads = [x for x in tidy(text, unit).splitlines() if x.startswith("#")]
        self.assertEqual(heads, ["## Fixed Assets", "### Assets", "#### General", "### Dashboard"])
