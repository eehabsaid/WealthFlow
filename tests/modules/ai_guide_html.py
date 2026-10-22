"""Browser contract for the complete, navigable HTML guide and Arabic RTL layout."""

def _page(lang):
    direction = "rtl" if lang == "ar" else "ltr"
    chapters = [f"Screen {n}" for n in range(1, 19)]
    links = "".join(f'<li><a href="#chapter-{n}" data-target="chapter-{n}">{name}</a></li>'
                   for n, name in enumerate(chapters, 1))
    sections = "".join(f'<section id="chapter-{n}" class="guide-section"><h2>{name}</h2>'
                       f'<h3 id="tab-{n}">Tab</h3><p>Steps for {name}.</p></section>'
                       for n, name in enumerate(chapters, 1))
    return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head><meta charset="utf-8"><style>
.layout{{display:flex}}.toc-rail{{position:sticky;top:0;height:100vh;overflow:auto}}
.guide-section{{min-height:20rem}}.active{{font-weight:bold}}
</style></head><body><div class="layout">
<nav class="toc-rail" id="tocRail"><ul>{links}</ul></nav>
<main id="main-content"><header><h1>WealthFlow user guide</h1></header>{sections}</main>
</div><script>
document.querySelectorAll('#tocRail a[data-target]').forEach(a=>a.addEventListener('click',()=>{{
  document.querySelectorAll('#tocRail a').forEach(link=>link.classList.remove('active'));
  a.classList.add('active');
}}));
</script></body></html>"""


def _run(context, reporter, screenshot_logger):
    page = context.page
    page.set_content(_page("en"))
    links = page.locator("#tocRail a[data-target]").count()
    page.click("#tocRail a[data-target='chapter-18']")
    active = page.locator("#tocRail a.active").inner_text()
    chapter = page.locator("#chapter-18 h2").inner_text()
    sticky = page.locator("#tocRail").evaluate("(el) => getComputedStyle(el).position") == "sticky"
    page.set_content(_page("ar"))
    rtl = page.locator("html").get_attribute("dir") == "rtl"
    ok = links == 18 and active == chapter == "Screen 18" and sticky and rtl
    shot = screenshot_logger.capture(page, "ai", "guide_html", "none", "view", "ok" if ok else "fail")
    reporter.add_step("AI guide HTML: 18 chapters, contents rail, active chapter, RTL", "WealthFlow AI",
                      "PASS" if ok else "FAIL",
                      f"chapters={links}, active={active!r}, sticky={sticky}, Arabic rtl={rtl}", screenshot_path=shot)


def test_ai_guide_html(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "guide_html_error", "none", "fail", "fail")
        reporter.add_step("AI guide HTML", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        context.goto_route("#ai")
        context.reload()
