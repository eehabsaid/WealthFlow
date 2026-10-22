"""Opt-in acceptance test using the configured local Ollama model."""

from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, tag

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.services.ai.exports.builders.guide_html import build_guide_html
from core.services.ai.exports.document import ExportDocument, parse_markdown
from core.services.ai.investigation.compose_sections import units
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import make_user


@tag("real_ollama")
class RealOllamaGuideTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("ollama_guide_admin", sysadmin=True)

    def _provider(self):
        if os.getenv("WEALTHFLOW_REAL_OLLAMA_TESTS") != "1":
            self.skipTest("Set WEALTHFLOW_REAL_OLLAMA_TESTS=1 to run local-model acceptance.")
        model = os.getenv("WEALTHFLOW_REAL_OLLAMA_MODEL")
        if not model:
            self.skipTest("Set WEALTHFLOW_REAL_OLLAMA_MODEL to the configured local model.")
        provider = OllamaProvider(base_url=os.getenv("WEALTHFLOW_REAL_OLLAMA_URL", "http://127.0.0.1:11434"),
                                  model=model, timeout=240)
        provider.user_options["context_size"] = os.getenv("WEALTHFLOW_REAL_OLLAMA_CONTEXT", "32768")
        return provider

    def test_multilingual_ask_and_agent_guides(self):
        provider = self._provider()
        cases = (
            ("en", "Write a complete HTML user guide for the WealthFlow app.", "ask", "off"),
            ("ar", "اكتب دليل مستخدم كامل للتطبيق WealthFlow بصيغة HTML.", "agent", "on"),
            ("fr", "Rédige un guide utilisateur HTML complet de l’application WealthFlow.", "ask", "on"),
            ("de", "Schreibe eine vollständige HTML-Bedienungsanleitung für die WealthFlow-App.", "agent", "off"),
        )
        expected_chapters = {unit["heading"] for unit in units(self.admin) if unit["heading"]}
        for lang, request, mode, thinking in cases:
            with self.subTest(language=lang, mode=mode, thinking=thinking):
                result = SimpleNamespace(content="Let me write the guide.", steps=[], results=[], reason="answered",
                                         llm_calls=0, cut_off=False, cancelled=False)
                if mode == "agent":
                    result.steps.append({"tool": "generate_file", "status": "success",
                                         "arguments": {"content": "<h1>Short model draft</h1>"}})
                with patch("core.integrations.ai_provider.ollama_payload.think_setting", return_value=thinking):
                    self.assertTrue(ensure_document(provider, request, result, 24000, self.admin, None))
                document = ExportDocument(title="WealthFlow user guide", generated="", lang=lang,
                                          blocks=parse_markdown(result.content), source=result.content)
                html = build_guide_html(document, lang).decode("utf-8")
                headings = {unit["heading"] for unit in units(self.admin) if unit["heading"]}
                self.assertEqual(len(headings), 18)
                self.assertEqual(len(re.findall(r'class="guide-section"', html)), 18)
                paragraphs = re.findall(r'<p class="purpose">(.*?)</p>', html)
                self.assertEqual(len(paragraphs), len({p.casefold() for p in paragraphs}))
                self.assertIn('id="tocRail"', html)
                self.assertIn(f'<html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}">', html)
                output_dir = os.getenv("WEALTHFLOW_REAL_OLLAMA_OUTPUT_DIR")
                if output_dir:
                    path = Path(output_dir)
                    path.mkdir(parents=True, exist_ok=True)
                    (path / f"user_guide_{lang}.html").write_text(html, encoding="utf-8")

    def test_standalone_login_page_is_kept_as_model_output(self):
        provider = self._provider()
        login = provider.generate(
            [{"role": "system", "content": "Return only a complete standalone HTML document."},
             {"role": "user", "content": "Write me an HTML login page."}],
            tools=None, temperature=0.2, max_tokens=6000, reasoning="off", timeout=240,
        )
        login_html = login.get("content", "")
        self.assertRegex(login_html, r"(?is)<html\b")
        result = SimpleNamespace(content=login_html, steps=[], results=[], reason="answered", llm_calls=0,
                                 cut_off=False, cancelled=False)
        self.assertFalse(ensure_document(provider, "Write me an HTML login page.", result, 24000, self.admin, None))
        self.assertEqual(result.content, login_html)
