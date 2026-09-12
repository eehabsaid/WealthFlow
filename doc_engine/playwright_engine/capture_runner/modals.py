"""ModalsMixin: tab-click helpers and generic modal discovery/capture. See
this package's __init__.py for the sibling list and composition
conventions."""
from typing import Dict, List, Any

from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log, check_cancelled_and_exit


class ModalsMixin:
    def click_tab_by_id(self, page: Page, tab: Dict[str, Any]) -> bool:
        self.ensure_modals_closed(page)
        return page.evaluate("""(tabData) => {
            const main = document.getElementById('main-content');
            if (!main) return false;

            let target = null;
            if (tabData.id) {
                const candidates = Array.from(main.querySelectorAll(`[onclick*="${tabData.id}"], [data-bs-target*="${tabData.id}"]`));
                target = candidates.find(el => el.offsetParent !== null && !el.closest('.d-none'));
                if (!target) {
                    const byId = main.querySelector('#' + tabData.id + '-tab, #' + tabData.id);
                    if (byId) target = byId;
                }
            }
            if (!target) {
                const elements = Array.from(main.querySelectorAll('button, .nav-link, .nav-item, [role="tab"], .dropdown-item, .wf-dropdown-item'));
                const normalize = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
                const normText = normalize(tabData.name);
                let matches = elements.filter(el => el.offsetParent !== null && !el.classList.contains('dropdown-toggle') && !el.closest('.d-none'));
                target = matches.find(el => el.textContent.trim().toLowerCase() === tabData.name.toLowerCase());
                if (!target) target = matches.find(el => normalize(el.textContent) === normText);
                if (!target) target = matches.find(el => normalize(el.textContent).includes(normText));
            }
            if (target) {
                const isBootstrapTab = target.hasAttribute('data-bs-toggle') || target.hasAttribute('data-bs-target');
                if (isBootstrapTab && window.bootstrap && window.bootstrap.Tab) {
                    window.bootstrap.Tab.getOrCreateInstance(target).show();
                } else {
                    target.scrollIntoView({ behavior: 'auto', block: 'center' });
                    target.click();
                }
                return true;
            }
            return false;
        }""", tab)

    def _extract_triggered_fn_names(self, nested_nav: List[Dict[str, Any]]) -> List[str]:
        """
        Pulls out every JS function name (including dotted paths like
        'window.KB.newForm' -> 'KB.newForm') referenced in
        nested_navigation's explicit triggers, normalized the same way the
        generic auto-discovery pass normalizes real onclick attributes
        (stripping a leading 'window.'). Used so the generic pass never
        re-captures a modal that's already explicitly and precisely handled
        in inventory.json - avoiding duplicate screenshots.
        """
        import re
        names = set()
        control_keywords = {"if", "eval", "settimeout", "function", "for", "while", "else"}
        for m in nested_nav or []:
            trigger = m.get("trigger", "") or ""
            for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_.]*)\s*\(', trigger):
                fn = match.group(1)
                if fn.lower() in control_keywords:
                    continue
                normalized = fn[len("window."):] if fn.startswith("window.") else fn
                names.add(normalized)
                # Also keep the last dotted segment as a fallback match target
                # (e.g. 'newForm' from 'KB.newForm'), since some real onclick
                # attributes in the app call it without the 'window.' prefix.
                if "." in normalized:
                    names.add(normalized.split(".")[-1])
        return list(names)

    def process_modals(self, page: Page, route_prefix: str, modals: List[Dict[str, Any]]) -> None:
        for modal in modals:
            check_cancelled_and_exit(self.manifest_service)
            try:
                log(f"  -> Opening modal: {modal['name']}")
                page.evaluate("""() => {
                    if (document.querySelector('.modal.show')) {
                        const closeBtn = document.querySelector('.modal.show .btn-close');
                        if (closeBtn) closeBtn.click();
                    }
                }""")
                page.wait_for_timeout(300)

                clicked = page.evaluate("""(modal) => {
                    const modalName = modal.name;
                    const trigger = modal.trigger;
                    const main = document.getElementById('main-content');
                    const safeButtons = main ? Array.from(main.querySelectorAll('button, a')).filter(b => b.offsetParent !== null && !b.closest('.d-none')) : [];
                    let target = null;
                    if (trigger) {
                        if (trigger.startsWith('eval:')) {
                            const code = trigger.substring(5);
                            try { eval(code); return true; } catch (e) { return false; }
                        }
                        target = safeButtons.find(b => 
                            (b.getAttribute('onclick') && b.getAttribute('onclick').toLowerCase().includes(trigger.toLowerCase())) ||
                            (b.title && b.title.toLowerCase().includes(trigger.toLowerCase())) ||
                            (b.id && b.id.toLowerCase().includes(trigger.toLowerCase())) ||
                            (b.getAttribute('data-bs-target') && b.getAttribute('data-bs-target').toLowerCase().includes(trigger.toLowerCase()))
                        );
                    }
                    if (!target) {
                        target = safeButtons.find(b => b.textContent.toLowerCase().includes(modalName.toLowerCase()));
                    }
                    if (target) { target.click(); return true; }
                    return false;
                }""", modal)



                if not clicked:
                    log(f"     Cannot find trigger for modal: {modal['name']}. Skipping.")
                    continue

                self.global_context["modal_id"] = sanitize_filename(modal['name'])
                self.global_context["modal_order"] = modal.get("order", 0)
                self.global_context["page_title"] = modal.get("name") or None
                self.capture_modal_tabs(page, f"{route_prefix}_{sanitize_filename(modal['name'])}", close_after=True)
                self.ensure_modals_closed(page)
                self.global_context["modal_id"] = None
                self.global_context["modal_order"] = 0
            except Exception as err:
                log(f"  Failed processing modal {modal['name']}: {err}")
                self.ensure_modals_closed(page)

