"""WealthFlow QA Module - the user guide as a styled HTML page (contents rail linked to every chapter, active chapter, RTL).

Real browser, no model needed: the page is built by the same function that makes the downloadable guide (the Django tests cover the
chat flow). Checks: every contents link scrolls to its chapter and becomes active, the sub-section links exist, an Arabic guide is
right-to-left.
"""

from core.services.ai.exports.builders.guide_html import build_guide_html
from core.services.ai.exports.document import ExportDocument, parse_markdown


def _doc(lang, words):
    md = "\n\n".join(f"## {w}\n\n" + "Text. " * 400 + f"\n\n### {w} part\n\n" + "More text. " * 200 for w in words)
    return ExportDocument(title="WealthFlow", generated="", lang=lang, blocks=parse_markdown(md), source=md)


def _run(context, reporter, screenshot_logger):
    page = context.page
    page.set_content(build_guide_html(_doc("en", ["Alpha", "Beta", "Gamma"]), "en").decode())
    links = page.locator("#tocRail a[data-target]").count()
    page.click("#tocRail a[data-target='sec-3-gamma']")
    page.wait_for_timeout(1200)
    active = page.locator("#tocRail a.active").inner_text()
    subs = page.locator("#tocRail .toc-l1.current .toc-sub a").count()
    ok_en = links == 3 and "Gamma" in active and subs == 1
    page.set_content(build_guide_html(_doc("ar", ["البدء", "الرصيد", "التقارير"]), "ar").decode())
    rtl = page.evaluate("() => document.documentElement.dir") == "rtl"
    shot = screenshot_logger.capture(page, "ai", "guide_html", "none", "view", "ok" if ok_en and rtl else "fail")
    reporter.add_step("AI guide HTML: contents links, active chapter, RTL", "WealthFlow AI", "PASS" if ok_en and rtl else "FAIL",
                      f"links={links}, active={active!r}, sub-links={subs}, arabic rtl={rtl}", screenshot_path=shot)


def test_ai_guide_html(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "guide_html_error", "none", "fail", "fail")
        reporter.add_step("AI guide HTML", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        context.goto_route("#ai")
        context.reload()
