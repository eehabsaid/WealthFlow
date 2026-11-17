"""Settings > Documentation: the coding agent has its own chapter (it is not a web page, so the screenshot capture never finds it). It is in the admin and technical guides,
not in the user guide, its titles exist in all four languages, and its text matches the real commands."""

import json
import os
import tempfile

from django.test import SimpleTestCase

from ai.doc_engine.config import CONTENT_FILE
from ai.doc_engine.document_generator.labels import fixed_labels
from ai.doc_engine.document_generator.naming import NamingMixin
from ai.doc_engine.document_generator.translation import TranslationMixin
from ai.doc_engine.document_generator.validation import I18N_DIR
from ai.doc_engine.extra_sections import TITLE, extra_nodes
from ai.doc_engine.guides import AdminGuideGenerator, TechnicalGuideGenerator, UserGuideGenerator
from ai.doc_engine.models import DocumentationModel
from ai.doc_engine.renderers.markdown_renderer import MarkdownRenderer


def content():
    with open(CONTENT_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def locale(lang):
    with open(os.path.join(I18N_DIR, f"{lang}.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Translator(TranslationMixin):
    def __init__(self, lang):
        self.translations, self.reverse_en, self.validation_warnings = locale(lang), {}, []


class DevAgentChapterTests(SimpleTestCase):
    def setUp(self):
        self.model = DocumentationModel({"pages": []}, content())

    def test_the_chapter_has_its_three_parts_and_real_text(self):
        (top,) = [n for n in self.model.nodes if n.id == "dev-agent"]
        self.assertEqual([c.id for c in top.children], ["dev-agent::settings", "dev-agent::run", "dev-agent::training"])
        text = json.dumps([top.purpose, top.steps] + [[c.purpose, c.steps] for c in top.children])
        for real in ("python -m ai.dev_agent settings set reserve_tokens", "scripts/traj_run.py", "--stages evaluate", "FAILED", "NO CHANGE NEEDED"):
            self.assertIn(real, text)
        self.assertEqual(self.model.validation_warnings, [])

    def test_admin_and_technical_guides_have_it_and_the_user_guide_does_not(self):
        ids = lambda gen: [n.id for n in gen(self.model).filter_model()]   # noqa: E731
        self.assertIn("dev-agent", ids(AdminGuideGenerator))
        self.assertIn("dev-agent", ids(TechnicalGuideGenerator))
        self.assertNotIn("dev-agent", ids(UserGuideGenerator))

    def test_titles_exist_and_differ_in_every_language(self):
        keys = [TITLE] + [c.title for c in extra_nodes(content())[0].children]
        titles = {}
        for lang in ("en", "ar", "fr", "de"):
            data = locale(lang)
            self.assertEqual([k for k in keys if not data.get(k)], [], lang)
            titles[lang] = Translator(lang)._t_title(TITLE)
        self.assertEqual(titles["en"], "Coding Agent")
        self.assertEqual(len(set(titles.values())), 4)

    def test_without_its_content_there_is_simply_no_chapter(self):
        self.assertEqual(extra_nodes({}), [])


    def test_the_real_markdown_renderer_writes_the_chapter_in_french_with_its_steps(self):
        flat = NamingMixin()._flatten_tree(AdminGuideGenerator(self.model).filter_model())
        tr = Translator("fr")
        for node in flat:
            node.title, node.navigation = tr._t_title(node.title), [tr._t_title(x) for x in node.navigation]
        context = {**fixed_labels(tr.translations), "app_name": "WealthFlow", "guide_type": "Admin", "title": "T", "date": "2026-11-17", "language": "FR", "theme": "Dark",
                   "device": "Desktop", "version": "1.0", "page_title": "T", "is_technical": False}
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "g.md")
            MarkdownRenderer().render(flat, out, context)
            text = open(out, encoding="utf-8").read()
        for expected in ("Agent de codage", "Paramètres de l'agent", "Entraînement de l'agent", "python -m ai.dev_agent settings"):
            self.assertIn(expected, text)
