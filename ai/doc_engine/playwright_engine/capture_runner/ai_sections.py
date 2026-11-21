"""AiSectionsMixin: Settings > AI Advisor shows one section at a time (tab bar), so the documentation photographs each section on
its own, as a nested tab of the AI Advisor tab. See this package's __init__.py for the sibling list and composition conventions."""
from playwright.sync_api import Page

from ai.doc_engine.services.navigation_planner import sanitize_filename
from ai.doc_engine.playwright_engine.capture_runner.helpers import log, check_cancelled_and_exit

AI_ADVISOR_TAB_ID = "settings-aiadvisor"

# [{id, key (its i18n key, the documentation key), title}] of every section the page offers now (the Usage limits one only for the system administrator, once it has loaded),
# plus the id of the section that is open. Reads the page's own list, so a section added later is captured without a code change.
SECTIONS_JS = r"""() => {
  const ui = window.AIA && window.AIA.ui;
  if (!ui || !ui.GROUPS) return null;
  const chip = (id) => document.querySelector('.aia-chip[data-aia-target="' + id + '"]');
  const out = ui.GROUPS.concat([ui.LIMITS_NAV]).filter(g => g && document.querySelector('[data-aia-group="' + g[0] + '"]'))
    .filter(g => g[0] !== 'limits' || (chip('limits') && !chip('limits').hidden))
    .map(g => ({ id: g[0], key: g[2], title: (chip(g[0]) && chip(g[0]).textContent.trim()) || g[3] }));
  return { sections: out, active: (window.AIA.state && window.AIA.state.activeGroup) || null };
}"""


class AiSectionsMixin:
    def capture_ai_advisor_sections(self, page: Page, prefix: str) -> None:
        """One screenshot per AI Advisor section (the open one is already the tab's own screenshot)."""
        info = page.evaluate(SECTIONS_JS)
        if not info or not info.get("sections"):
            log("     AI Advisor sections not found. Skipping them.")
            return
        for section in info["sections"]:
            check_cancelled_and_exit(self.manifest_service)
            if section["id"] == info.get("active") or section["id"] == "provider":
                continue
            if not page.evaluate("(id) => !!(window.AIA.ui.showGroup && window.AIA.ui.showGroup(id))", section["id"]):
                continue
            log(f"        -> Capturing AI Advisor section: {section['title']}")
            page.wait_for_timeout(300)
            self.global_context["nested_tab_id"] = section["key"]
            self.global_context["page_title"] = section["title"] or None
            self.capture_screenshot(page, f"{prefix}_{sanitize_filename(section['id'])}")
            self.global_context["nested_tab_id"] = None
        page.evaluate("() => window.AIA.ui.showGroup('provider')")
