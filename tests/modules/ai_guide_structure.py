"""Guide files: chapters are numbered and each starts on its own page in Word and PDF, and a long guide's PDF contents lists only
its chapters. The files are built by the app's real builders (run inside the disposable Django, so this module imports no core.*)
and checked here from the bytes, then the AI screen is shown for the screenshot record."""

import base64
import json
import re
import zipfile
from io import BytesIO

from tests.modules.e2e_settings import django_exec

CHAPTERS, TABS = 17, 6
_BUILD = f"""
import base64, json
from core.services.ai.exports.document import ExportDocument, parse_markdown
from core.services.ai.exports.registry import get_format
text = "This page lets you manage the records of the application in a clear way for every user."
md = "".join(f"## Screen {{i}}\\n\\n{{text}}\\n\\n" + "".join(f"### Tab {{i}}-{{j}}\\n\\n{{text}} {{j}}\\n\\n" for j in range({TABS})) for i in range(1, {CHAPTERS + 1}))
doc = ExportDocument(title="Guide", generated="2026", lang="en", blocks=parse_markdown(md), source=md)
out = {{k: base64.b64encode(get_format(k).builder(doc, "en")).decode() for k in ("docx", "pdf")}}
print("GUIDE_FILES:" + json.dumps(out))
"""


def _files():
    raw = next(line for line in django_exec(_BUILD).splitlines() if line.startswith("GUIDE_FILES:"))
    return {k: base64.b64decode(v) for k, v in json.loads(raw[len("GUIDE_FILES:"):]).items()}


def _word_checks(data):
    xml = zipfile.ZipFile(BytesIO(data)).read("word/document.xml").decode("utf8")
    breaks = len(re.findall(r"<w:pageBreakBefore(?: w:val=\"(?:1|true|on)\")?/>", xml))
    return breaks == CHAPTERS - 1 and "1 Screen 1" in xml and f"{CHAPTERS} Screen {CHAPTERS}" in xml, f"page_breaks={breaks}"


def _pdf_checks(data):
    import pypdf

    reader = pypdf.PdfReader(BytesIO(data))
    first = reader.pages[0].extract_text() or ""
    ok = len(reader.pages) >= CHAPTERS + 1 and f"Screen {CHAPTERS}" in first and "Tab 3-2" not in first
    return ok and sum(len(o) for o in reader.outline if isinstance(o, list)) == CHAPTERS * TABS, f"pages={len(reader.pages)}"


def _run(context, reporter, screenshot_logger):
    files = _files()
    word_ok, word_detail = _word_checks(files["docx"])
    pdf_ok, pdf_detail = _pdf_checks(files["pdf"])
    context.goto_route("#ai")
    for name, ok, detail in (("Word guide: numbered chapters, a page per chapter", word_ok, word_detail),
                             ("PDF guide: a page per chapter, chapters-only contents, tabs in the outline", pdf_ok, pdf_detail)):
        shot = screenshot_logger.capture(context.page, "ai", "guide_structure", "none", "view", "ok" if ok else "fail")
        reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def test_ai_guide_structure(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "guide_structure_error", "none", "fail", "fail")
        reporter.add_step("AI guide files structure", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
