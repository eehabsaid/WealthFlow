"""Live screenshots in the AI user guide: placement in the text, owner-scoped storage and URL, Word / PDF / HTML export, switches."""

import io
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.services.exports.builders.docx import _build as build_docx
from ai.services.exports.builders.guide_html import build_guide_html
from ai.services.exports.builders.pdf import _build as build_pdf
from ai.services.exports.build import with_images
from ai.services.exports.document import ExportDocument, parse_markdown
from ai.services.guide_shots import add_screenshots, store
from ai.services.guide_shots.markers import insert
from ai.services.guide_shots.plan import targets
from ai.services.guide_shots.settings import KEYS, blur, enabled
from ai.models import AISetting

User = get_user_model()


def _jpeg() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (40, 24), "white").save(buf, "JPEG")
    return buf.getvalue()


PLAN = [
    {"key": "aaaaaaaaaaaa", "route": "budgets", "title": "Budgets", "tab": None},
    {"key": "bbbbbbbbbbbb", "route": "budgets", "title": "Overview", "tab": {"id": "ov", "name": "Overview"}},
    {"key": "cccccccccccc", "route": "gold", "title": "Gold Price", "tab": None},
]
GUIDE = "# Guide\n\n## Signing up\n\nText\n\n## Budgets\n\nText\n\n### Overview\n\nText\n\n## Gold Price\n\nText\n"


class MarkersTests(TestCase):
    def test_images_go_under_matching_headings_only_when_captured(self):
        out = insert(GUIDE, PLAN, {"aaaaaaaaaaaa", "bbbbbbbbbbbb"})
        self.assertIn("## Budgets\n\n![Budgets](" + store.URL.format(key="aaaaaaaaaaaa") + ")", out)
        self.assertIn("### Overview\n\n![Overview](" + store.URL.format(key="bbbbbbbbbbbb") + ")", out)
        self.assertNotIn("cccccccccccc", out)
        self.assertNotIn("Signing up\n\n![", out)

    def test_translated_headings_match_by_position(self):
        text = "# دليل\n\n## التسجيل\n\nx\n\n## الميزانيات\n\nx\n\n### نظرة عامة\n\nx\n\n## سعر الذهب\n\nx\n"
        out = insert(text, PLAN, {"aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"})
        self.assertIn("## الميزانيات\n\n![", out)
        self.assertIn("### نظرة عامة\n\n![", out)
        self.assertIn("## سعر الذهب\n\n![", out)


class ExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("shot_user", password="x")
        self.other = User.objects.create_user("other_user", password="x")
        store.save(self.user.pk, "aaaaaaaaaaaa", _jpeg())
        store.save(self.user.pk, "bbbbbbbbbbbb", _jpeg())
        text = insert(GUIDE, PLAN, {"aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"})
        self.blocks = parse_markdown(text)

    def _doc(self, user):
        return ExportDocument(title="Guide", lang="en", blocks=with_images(self.blocks, user), source="## a\n## b\n## c")

    def test_image_lines_parse_and_other_users_files_are_dropped(self):
        self.assertEqual([b.key for b in self.blocks if b.kind == "image"], ["aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"])
        self.assertEqual(len([b for b in self._doc(self.user).blocks if b.kind == "image"]), 2)   # the third file does not exist
        self.assertEqual(len([b for b in self._doc(self.other).blocks if b.kind == "image"]), 0)

    def test_word_pdf_and_html_carry_the_images(self):
        doc = self._doc(self.user)
        from docx import Document

        self.assertEqual(len(Document(io.BytesIO(build_docx(doc, "en"))).inline_shapes), 2)
        self.assertGreater(build_pdf(doc, "en").count(b"/Subtype /Image"), 0)
        self.assertEqual(build_guide_html(doc, "en").decode().count("data:image/jpeg;base64,"), 2)


class SwitchTests(TestCase):
    def test_defaults_on_and_settings_roundtrip(self):
        from ai.views.settings.ai_pipeline_settings import get_pipeline_settings, persist_pipeline_settings, validate_pipeline_settings

        self.assertTrue(enabled() and blur())
        validated, err = validate_pipeline_settings({"ai_guide_blur": False, "ai_guide_screenshots": "true"})
        self.assertIsNone(err)
        persist_pipeline_settings(validated)
        self.assertFalse(blur())
        self.assertTrue(enabled())
        self.assertIs(get_pipeline_settings()["ai_guide_blur"], False)

    def test_off_means_text_unchanged_and_no_browser(self):
        AISetting.set("ai_guide_screenshots", "false", user=None)
        user = User.objects.create_user("u2", password="x")
        with mock.patch("ai.services.guide_shots.apply.capture") as cap:
            self.assertEqual(add_screenshots(GUIDE, user), GUIDE)
        cap.assert_not_called()

    def test_failed_capture_leaves_guide_untouched_and_files_saved_when_ok(self):
        user = User.objects.create_user("u3", password="x")
        with mock.patch("ai.services.guide_shots.apply.capture", return_value={}):
            self.assertEqual(add_screenshots(GUIDE, user), GUIDE)
        plan = targets(user, True)
        shots = {plan[0]["key"]: _jpeg()}
        with mock.patch("ai.services.guide_shots.apply.capture", return_value=shots):
            guide = f"# G\n\n## {plan[0]['title']}\n\nx\n\n## B\n\nx\n\n## C\n\nx\n"
            out = add_screenshots(guide, user)
        self.assertIn("guide-shots/" + plan[0]["key"], out)
        self.assertIsNotNone(store.read(user.pk, plan[0]["key"]))

    def test_not_a_guide_is_left_alone(self):
        user = User.objects.create_user("u4", password="x")
        self.assertEqual(add_screenshots("## one\n\ntext", user), "## one\n\ntext")
        self.assertEqual(set(KEYS), {"ai_guide_screenshots", "ai_guide_blur"})
