"""A guide asked for in Arabic is delivered in Arabic: the language is read from the request (a model that fails or answers oddly
cannot turn it into English) and a chunk the model keeps in English is translated line by line. Runs the app's real resolver and
translator inside the disposable Django (this module imports no core.*), then the Word file built from the result is checked."""

import json
import zipfile
from io import BytesIO

from tests.modules.e2e_settings import django_exec

_RUN = """
import base64, json, re
from ai.services.investigation.compose_language import target_language
from ai.services.investigation.compose_translate import translate_markdown, latin_share
from ai.services.exports.document import ExportDocument, parse_markdown
from ai.services.exports.registry import get_format
request = "generate a full user guide for the entire app as word, pdf, and html in well formatted Arabic"
silent = lambda system, content, temperature=0: ""
language = target_language(silent, request)
source = "## Signing up\\n\\nOpen it from the menu and create your account today.\\n\\n1. Click Create Account.\\n2. Enter your details.\\n\\n- Login: Sign in securely.\\n"
def model(system, content, temperature=0.1):
    if "one line of a user guide" not in system:
        return content        # a long reply that comes back unchanged
    return re.sub(r"[A-Za-z]+", "نص", content)
arabic = translate_markdown(model, lambda: False, source, language, 10**12, None, True)
doc = ExportDocument(title="دليل", generated="2026", lang="ar", blocks=parse_markdown(arabic), source=arabic)
print("RESULT:" + json.dumps({"language": language, "share": latin_share(arabic), "text": arabic,
                              "docx": base64.b64encode(get_format("docx").builder(doc, "ar")).decode()}))
"""


def _run(context, reporter, screenshot_logger):
    raw = next(line for line in django_exec(_RUN).splitlines() if line.startswith("RESULT:"))
    result = json.loads(raw[len("RESULT:"):])
    import base64

    xml = zipfile.ZipFile(BytesIO(base64.b64decode(result["docx"]))).read("word/document.xml").decode("utf8")
    ok = result["language"] == "Arabic" and result["share"] < 0.1 and "Open it" not in result["text"] and "w:bidi" in xml
    context.goto_route("#ai")
    shot = screenshot_logger.capture(context.page, "ai", "guide_language", "none", "view", "ok" if ok else "fail")
    reporter.add_step("Arabic guide request: language read from the request, chunks translated line by line, right-to-left Word file",
                      "WealthFlow AI", "PASS" if ok else "FAIL",
                      f"language={result['language']!r}, latin_share={result['share']:.2f}, bidi={'w:bidi' in xml}", screenshot_path=shot)


def test_ai_guide_language(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "guide_language_error", "none", "fail", "fail")
        reporter.add_step("AI guide language", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
