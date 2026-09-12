"""TableEditsMixin: per-row table Edit-modal capture pass. See this
package's __init__.py for the sibling list and composition conventions."""
from typing import List, Optional

from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log, check_cancelled_and_exit


class TableEditsMixin:
    def process_table_row_edits(self, page: Page, route_prefix: str, skip_fn_names: Optional[List[str]] = None) -> None:
        """
        Discovers and captures Add/Edit/View-style modals triggered by
        buttons ANYWHERE on the page or open modal - not just inside
        <table>/.card elements, so card-style triggers (e.g. clickable divs
        used by the AI Workspace context panel) are picked up automatically
        too. Buttons are matched against a strict opener-keyword allowlist
        and a hard denylist (see _ACTION_DENYLIST_KEYWORDS) that is always
        checked first, so nothing that inserts/updates/deletes/saves real
        data is ever clicked - only buttons that open a view/form/popup.

        skip_fn_names: onclick handler names already captured explicitly via
        inventory.json's nested_navigation for this page/tab, so this
        generic pass doesn't capture (and duplicate) the same modal twice.
        """
        if route_prefix.startswith('fixed_assets') or 'fixed_assets' in route_prefix or route_prefix.startswith('salary_') or route_prefix.startswith('employment_') or 'employment' in route_prefix or 'salary' in route_prefix:
            return

        skip_set = set(skip_fn_names or [])

        candidate_buttons = page.evaluate("""(cfg) => {
            const denylist = cfg.denylist;
            const allowlist = cfg.allowlist;
            const els = Array.from(document.querySelectorAll(
                'table button, .table button, table a, .table a, .card button, ' +
                'button[onclick], a[onclick], div[onclick], [role="button"][onclick]'
            ));
            const matches = els.filter(b => {
                if (b.closest('#sidebar') || b.closest('.modal')) return false;
                if (b.offsetParent === null || b.closest('.d-none') || b.closest('.tab-pane:not(.active)')) return false;
                const onclick = (b.getAttribute('onclick') || '').toLowerCase();
                const title = (b.getAttribute('title') || '').toLowerCase();
                const text = b.textContent.trim().toLowerCase();
                const html = b.innerHTML.toLowerCase();
                const haystack = onclick + ' ' + title + ' ' + text;

                // Hard safety boundary: never even consider a denylisted action.
                for (const bad of denylist) {
                    if (haystack.includes(bad)) return false;
                }

                const iconMatch = html.includes('fa-pencil') || html.includes('fa-edit') ||
                                   html.includes('bi-pencil') || html.includes('btn-edit') ||
                                   html.includes('fa-plus') || html.includes('bi-plus');
                const keywordMatch = allowlist.some(k => haystack.includes(k));
                return iconMatch || keywordMatch;
            });

            const map = new Map();
            for (const btn of matches) {
                const onclick = btn.getAttribute('onclick') || '';
                const fnName = onclick.split('(')[0].trim() || btn.getAttribute('title') || btn.textContent.trim() || 'open_action';
                if (fnName && !map.has(fnName)) {
                    map.set(fnName, { fnName, onclick, text: btn.textContent.trim(), title: btn.getAttribute('title') });
                }
            }
            return Array.from(map.values());
        }""", {"denylist": self._ACTION_DENYLIST_KEYWORDS, "allowlist": self._OPENER_INCLUDE_KEYWORDS})

        if not candidate_buttons or len(candidate_buttons) == 0:
            return

        for idx, btn_info in enumerate(candidate_buttons):
            check_cancelled_and_exit(self.manifest_service)
            fn_name = btn_info.get("fnName") or f"open_action_{idx+1}"
            clean_fn_key = fn_name.replace('window.', '').replace('async', '').strip()

            if clean_fn_key in skip_set:
                continue

            clean_fn = sanitize_filename(clean_fn_key)
            display_label = btn_info.get("text") or btn_info.get("title") or fn_name
            log(f"  -> [AUTO-DISCOVERED] Opening trigger not in inventory.json: {display_label} ({fn_name})")

            opened = page.evaluate("""(info) => {
                const els = Array.from(document.querySelectorAll(
                    'table button, .table button, table a, .table a, .card button, ' +
                    'button[onclick], a[onclick], div[onclick], [role="button"][onclick]'
                ));
                const matches = els.filter(b => !b.closest('#sidebar') && !b.closest('.modal') && b.offsetParent !== null && !b.closest('.d-none') && !b.closest('.tab-pane:not(.active)'));
                let target = matches.find(b => (b.getAttribute('onclick') || '').includes(info.fnName));
                if (!target && info.onclick) {
                    target = matches.find(b => b.getAttribute('onclick') == info.onclick);
                }
                if (target) {
                    target.scrollIntoView({ behavior: 'auto', block: 'center' });
                    target.click();
                    return true;
                }
                return false;
            }""", btn_info)

            if opened:
                try:
                    page.wait_for_selector('.modal.show', timeout=3000)
                    modal_name = f"auto_{clean_fn}"
                    self.capture_modal_tabs(page, f"{route_prefix}_{modal_name}", close_after=True)
                except Exception as e:
                    log(f"     Auto-discovered trigger for {fn_name} did not open a modal (may just toggle inline UI): {e}")
                finally:
                    self.ensure_modals_closed(page)


