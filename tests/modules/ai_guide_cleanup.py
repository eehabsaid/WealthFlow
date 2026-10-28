"""Guide files, second round: the PDF contents of the current guide (18 chapters + 52 tabs) fits one page in English and Arabic
(chapter 1 starts on page 2, every tab still in the outline panel), and the translation clean-up: no literal asterisks, no word
written twice in a row, and a translation that loses a numbered step is rejected. The app's real builders and checks run inside
the disposable Django (this module imports no core.*) and the results are checked here from the bytes."""

import base64
import json
from io import BytesIO

from tests.modules.e2e_settings import django_exec

CHAPTERS, TABS = 18, 52
_CODE = r'''
import base64, json
from core.services.ai.exports.document import ExportDocument, parse_markdown
from core.services.ai.exports.registry import get_format
from core.services.ai.investigation.compose_polish import drop_doubled_words, strip_emphasis
from core.services.ai.investigation.compose_translate import rejection

PER = [3] * 16 + [2, 2]
NAMES = {"en": ("Screen", "Tab"), "ar": ("الشاشة", "التبويب")}
out = {}
for lang, (screen, tab) in NAMES.items():
    md = "".join(f"## {screen} {i}\n\nText.\n\n" + "".join(f"### {tab} {i}-{j}\n\nText {j}\n\n" for j in range(PER[i - 1])) for i in range(1, 19))
    doc = ExportDocument(title="Guide", generated="2026", lang=lang, blocks=parse_markdown(md), source=md)
    out[lang] = base64.b64encode(get_format("pdf").builder(doc, lang)).decode()
source = "Intro line.\n\n1. Open the page now.\n2. Click the button.\n3. Enter your password."
prose = "Introduction.\n\nOuvrez la page puis cliquez sur le bouton et saisissez le mot de passe."
steps = "Introduction.\n\n1. Ouvrez la page.\n2. Cliquez sur le bouton.\n3. Saisissez le mot de passe."
out["polish"] = {
    "asterisks": strip_emphasis("5. *نشر المعاملات الدخول*\n**bold** and * item"),
    "doubled": drop_doubled_words("تلك اللغة اللغة النشطة (اللغة) اللغة 5 5"),
    "prose": rejection(source, prose, False, False),
    "steps": rejection(source, steps, False, False),
}
print("GUIDE_CLEANUP:" + json.dumps(out))
'''


def _built() -> dict:
    raw = next(line for line in django_exec(_CODE).splitlines() if line.startswith("GUIDE_CLEANUP:"))
    return json.loads(raw[len("GUIDE_CLEANUP:"):])


def _outline(reader):
    found = []

    def walk(items):
        for item in items:
            walk(item) if isinstance(item, list) else found.append((item.title, reader.get_destination_page_number(item) + 1))
    walk(reader.outline)
    return found


def _pdf_checks(data: bytes):
    import pypdf

    reader = pypdf.PdfReader(BytesIO(data))
    outline = _outline(reader)
    return len(outline) == CHAPTERS + TABS and outline[0][1] == 2, f"entries={len(outline)}, first chapter on page {outline[0][1] if outline else '?'}"


def _polish_checks(p: dict):
    ok = (p["asterisks"] == "5. نشر المعاملات الدخول\n**bold** and * item" and p["doubled"] == "تلك اللغة النشطة (اللغة) اللغة 5 5"
          and p["prose"] == "numbered steps lost" and p["steps"] == "")
    return ok, json.dumps(p, ensure_ascii=False)[:200]


def _run(context, reporter, screenshot_logger):
    built = _built()
    en_ok, en_detail = _pdf_checks(base64.b64decode(built["en"]))
    ar_ok, ar_detail = _pdf_checks(base64.b64decode(built["ar"]))
    polish_ok, polish_detail = _polish_checks(built["polish"])
    context.goto_route("#ai")
    for name, ok, detail in (("PDF guide (English): contents on one page, tabs in the outline", en_ok, en_detail),
                             ("PDF guide (Arabic): contents on one page, tabs in the outline", ar_ok, ar_detail),
                             ("Translated guide clean-up: no asterisks, no doubled word, numbered steps kept", polish_ok, polish_detail)):
        shot = screenshot_logger.capture(context.page, "ai", "guide_cleanup", "none", "view", "ok" if ok else "fail")
        reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def test_ai_guide_cleanup(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "guide_cleanup_error", "none", "fail", "fail")
        reporter.add_step("AI guide contents and translation clean-up", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
