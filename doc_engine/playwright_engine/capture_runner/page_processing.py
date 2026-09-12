"""PageProcessingMixin: per-page capture orchestration (nav, tabs, modals,
screenshots) for a single inventory item. See this package's __init__.py
for the sibling list and composition conventions."""
from typing import Any, Dict

from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename, safe_filename
from .helpers import log, check_cancelled_and_exit


class PageProcessingMixin:
    def process_page(self, page: Page, item: Dict[str, Any]) -> None:
        route = item.get("route", "")
        title = item.get("title", "")
        log(f"\nNavigating to {route} ({title})")

        custom_prefix = item.get("customPrefix")
        if custom_prefix:
            route_prefix = custom_prefix
        elif route.startswith('/'):
            route_prefix = sanitize_filename(route.replace('/', ''))
        else:
            route_prefix = sanitize_filename(route)

        self.ensure_modals_closed(page)
        full_url = self.planner.get_full_url(route)
        page.goto(full_url)
        self.wait_for_ui_ready(page)
        if self.planner.is_chart_route(route):
            self.wait_for_charts(page)

        tabs = item.get("tabs", [])
        nested_nav = item.get("nested_navigation", [])

        # Safety net: compare the LIVE page's rendered tab bar against what's
        # declared in inventory.json and append anything missing. Declared
        # tabs (and their hand-tuned ordering/nested_navigation) are never
        # touched - this only fills gaps.
        discovered_tabs = self.discover_page_tabs(page)
        if discovered_tabs:
            tabs = self.merge_discovered_tabs(route, tabs, discovered_tabs)

        if tabs and len(tabs) > 0:
            for tab in tabs:
                check_cancelled_and_exit(self.manifest_service)
                self.manifest_service.current_progress += 1
                self.manifest_service.update_status('running', title, tab.get("name", ""))

                def capture_tab_action(tab=tab):
                    log(f"  -> Clicking tab: {tab.get('name')}")
                    clicked = self.click_tab_by_id(page, tab)
                    if not clicked:
                        log(f"     Tab button not found for: {tab.get('name')}. Skipping screenshot.")
                        return
                    self.wait_for_ui_ready(page)
                    if self.planner.is_chart_route(route):
                        self.wait_for_charts(page)
                    else:
                        page.wait_for_timeout(1000)

                    tab_name = tab.get("name", "")
                    tab_id = tab.get("id")
                    self.global_context["tab_id"] = tab_id or safe_filename(tab_name, tab_id)
                    self.global_context["page_title"] = tab_name or None

                    if tab_name == 'Translation Coverage':
                        self.capture_screenshot(page, 'Translation Coverage')
                    else:
                        self.capture_screenshot(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}")

                    tab_nested_nav = tab.get("nested_navigation")
                    if route == 'fixed-assets' and tab_id == 'assets':
                        self.process_asset_rows(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}")
                    else:
                        if tab_nested_nav:
                            self.process_modals(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}", tab_nested_nav)
                        if route != 'fixed-assets':
                            # Always run the safety-net generic discovery too (not just
                            # when nested_navigation is absent), so any Add/Edit/View
                            # trigger not explicitly declared still gets captured. Triggers
                            # already fired above via nested_navigation are skipped to
                            # avoid duplicate screenshots.
                            skip_fn_names = self._extract_triggered_fn_names(tab_nested_nav)
                            self.process_table_row_edits(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}", skip_fn_names=skip_fn_names)

                    self.ensure_modals_closed(page)
                    self.global_context["tab_id"] = None

                try:
                    self.execute_with_retry(f"tab {tab.get('name')}", capture_tab_action)
                except Exception as err:
                    log(f"  Failed to capture tab {tab.get('name')}: {err}")
        else:
            check_cancelled_and_exit(self.manifest_service)
            self.manifest_service.current_progress += 1
            self.manifest_service.update_status('running', title)

            def capture_page_action():
                self.capture_screenshot(page, route_prefix)
                if nested_nav and not tabs:
                    self.process_modals(page, route_prefix, nested_nav)
                skip_fn_names = self._extract_triggered_fn_names(nested_nav)
                self.process_table_row_edits(page, route_prefix, skip_fn_names=skip_fn_names)


            try:
                self.execute_with_retry(f"page {title}", capture_page_action)
            except Exception as err:
                log(f"  Failed to capture page {title}: {err}")

