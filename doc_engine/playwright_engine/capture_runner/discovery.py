"""DiscoveryMixin: live sidebar/tab discovery and merging into the
declared inventory. See this package's __init__.py for the sibling list
and composition conventions."""
from typing import Dict, List, Any

from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log


class DiscoveryMixin:
    def discover_sidebar_routes(self, page: Page) -> List[Dict[str, str]]:
        """
        Reads the REAL rendered sidebar and extracts every navigable route,
        in the order they appear on screen. This is a safety net: if a page
        is added to the sidebar in the future but nobody remembers to add it
        to inventory.json, it still gets captured (with a basic single
        screenshot) instead of being silently skipped.
        Never clicks anything here - pure read-only DOM inspection.
        """
        try:
            return page.evaluate(r"""() => {
                const items = Array.from(document.querySelectorAll('#sidebar .nav-item[onclick*="navigate("]'));
                const seen = new Set();
                const results = [];
                for (const el of items) {
                    const onclick = el.getAttribute('onclick') || '';
                    const m = onclick.match(/navigate\(\s*['"]([^'"]+)['"]/);
                    if (!m) continue;
                    const route = m[1];
                    if (seen.has(route)) continue;
                    seen.add(route);
                    const label = el.querySelector('span')?.textContent?.trim() || route;
                    results.push({ route, title: label });
                }
                return results;
            }""")
        except Exception as e:
            log(f"[WARNING] Sidebar route discovery failed: {e}")
            return []

    def discover_page_tabs(self, page: Page) -> List[Dict[str, str]]:
        """
        Reads the REAL rendered page-level tab bar (the app's consistent
        '.wf-tab' convention used by Settings, Balance, Fixed Assets,
        Financial Advisor, etc.) and returns each tab's visible name, in
        DOM order. Used as a safety net to catch any tab not declared in
        inventory.json, regardless of which underlying mechanism that page
        uses to switch tabs (navigate(), Bootstrap data-bs-toggle, or a
        custom switch function) - we only need to know the button exists
        and can be clicked, not how it works internally.
        Never clicks anything here - pure read-only DOM inspection.
        """
        try:
            return page.evaluate(r"""() => {
                const bar = document.querySelector('#main-content .wf-tabs-row, #main-content [role="tablist"]');
                if (!bar) return [];
                const buttons = Array.from(bar.querySelectorAll('.wf-tab, [role="tab"]'));
                return buttons.map((b, i) => ({
                    name: b.textContent.trim(),
                    domIndex: i
                })).filter(t => t.name);
            }""")
        except Exception as e:
            log(f"[WARNING] Page tab discovery failed: {e}")
            return []

    def merge_discovered_tabs(self, route: str, declared_tabs: List[Dict[str, Any]], discovered_tabs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Appends any tab found live on the page that isn't already declared
        in inventory.json (matched by visible name, case-insensitive). Never
        removes or reorders declared tabs - only fills gaps, so hand-tuned
        ordering and nested_navigation for known tabs are preserved exactly.
        """
        declared_names = {str(t.get("name", "")).strip().lower() for t in declared_tabs}
        merged = list(declared_tabs)
        for dt in discovered_tabs:
            name = dt.get("name", "").strip()
            if not name or name.lower() in declared_names:
                continue
            log(f"  [AUTO-DISCOVERED] New tab found on '{route}' not in inventory.json: '{name}'. Capturing it automatically.")
            merged.append({
                "name": name,
                "id": sanitize_filename(name),
                "_auto_discovered": True,
            })
            declared_names.add(name.lower())
        return merged

    def merge_discovered_routes(self, inventory: List[Dict[str, Any]], discovered_routes: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Appends any sidebar route found live in the app that isn't already
        declared in inventory.json. Never removes or reorders declared
        routes. A discovered route is treated as already covered if it
        exactly matches a declared route, OR if it's a sub-route of one
        (e.g. the sidebar's Settings link goes straight to
        'settings-languages', which is really just the default tab of the
        already-declared 'settings' route with all 16 tabs) - otherwise
        we'd wrongly add a duplicate bare entry alongside the real one.
        """
        declared_routes = {str(item.get("route", "")) for item in inventory}
        merged = list(inventory)
        for r in discovered_routes:
            route = r.get("route", "")
            if not route:
                continue
            already_covered = any(
                route == d or route.startswith(d + "-") or d.startswith(route + "-")
                for d in declared_routes
            )
            if already_covered:
                continue
            log(f"  [AUTO-DISCOVERED] New sidebar page not in inventory.json: '{route}' ({r.get('title')}). Capturing it automatically.")
            merged.append({
                "route": route,
                "title": r.get("title") or route,
                "_auto_discovered": True,
            })
            declared_routes.add(route)
        return merged

    # Action buttons matching these keywords are NEVER auto-clicked, even if
    # they also match an "opener" keyword below. Checked first. This is the
    # hard safety boundary: nothing that inserts, updates, deletes, or saves
    # real data is ever triggered by the capture engine - only buttons whose
    # entire job is to open a view/form/popup are clicked.
    _ACTION_DENYLIST_KEYWORDS = [
        "delete", "remove", "destroy", "logout", "signout", "sign-out",
        "submit", "confirm", "save", "update", "pay", "checkout",
        "approve", "reject", "cancel", "promote", "finetune", "fine-tune",
        "generate", "scan", "sync", "export", "download", "print",
        "runbenchmark", "run_benchmark", "sendemail", "send_email",
    ]

    # Buttons are only considered candidates for auto-discovery if they
    # match one of these "opens something to look at" keywords.
    _OPENER_INCLUDE_KEYWORDS = [
        "edit", "add", "new", "show", "open", "view", "details", "manage",
        "history", "list", "search", "permission",
    ]

