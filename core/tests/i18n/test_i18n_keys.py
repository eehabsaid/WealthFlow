"""Guards the translation files: every literal key the UI asks for must exist
in all four languages, and the four files must define the same keys.

Keys built at runtime (a prefix + a variable, e.g. "error_" + code) cannot be
checked statically; they are recognised by a trailing underscore and skipped.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LANGS = ("en", "ar", "fr", "de")
_ATTR = re.compile(r'data-i18n(?:-placeholder|-title)?="([a-z][a-zA-Z0-9_]*)"')
_CALL = re.compile(r"(?<![\w.])t\(\s*[\"']([a-z][a-zA-Z0-9_]*)[\"']")


def _load(lang):
    path = Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _used_keys():
    root = Path(settings.BASE_DIR)
    files = list((root / "static" / "js").rglob("*.js"))
    files += list((root / "templates").rglob("*.html"))
    used = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in list(_ATTR.finditer(text)) + list(_CALL.finditer(text)):
            key = match.group(1)
            if not key.endswith("_"):
                used.setdefault(key, str(path.relative_to(root)))
    return used


class I18nKeyTests(SimpleTestCase):
    def test_every_used_key_exists_in_every_language(self):
        used = _used_keys()
        problems = []
        for lang in LANGS:
            data = _load(lang)
            problems += [f"{lang}: {k} (used in {f})" for k, f in sorted(used.items()) if k not in data]
        self.assertEqual(problems, [], "Missing translation keys:\n" + "\n".join(problems))

    def test_all_languages_define_the_same_keys(self):
        base = set(_load("en"))
        for lang in LANGS[1:]:
            keys = set(_load(lang))
            self.assertEqual(sorted(base - keys), [], f"{lang} is missing keys")
            self.assertEqual(sorted(keys - base), [], f"{lang} has extra keys")


class I18nPlaceholderTests(SimpleTestCase):
    def test_every_language_uses_the_same_placeholders_as_english(self):
        token = re.compile(r"\{[a-z_0-9]+\}")
        en = _load("en")
        problems = []
        for lang in LANGS[1:]:
            data = _load(lang)
            for key, value in en.items():
                if isinstance(value, str) and sorted(token.findall(value)) != sorted(token.findall(str(data.get(key, "")))):
                    problems.append(f"{lang}: {key}")
        self.assertEqual(problems, [], "Placeholder mismatch vs en:\n" + "\n".join(problems))

    def test_no_language_uses_the_retired_pivot_placeholder(self):
        for lang in LANGS:
            self.assertFalse([k for k, v in _load(lang).items() if isinstance(v, str) and "{pivot}" in v], lang)
