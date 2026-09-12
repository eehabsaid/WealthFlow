"""LifecycleMixin: engine construction and UI-readiness waits. See this
package's __init__.py for the sibling list and composition conventions."""
import os
from typing import Optional

from playwright.sync_api import Page

from doc_engine.config import LATEST_SCREENSHOTS_DIR, SCREENSHOTS_DIR
from doc_engine.services.inventory_provider import InventoryProvider
from doc_engine.services.navigation_planner import NavigationPlanner
from doc_engine.services.documentation_metadata_service import DocumentationMetadataService


class LifecycleMixin:
    def __init__(self, host: str = '127.0.0.1', port: str = '8001',
                 username: str = 'eehab_said', password: str = 'Eehabdev1',
                 theme: str = 'dark', language: str = 'en', device: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.theme = theme
        self.language = language
        self.device = device
        self.base_url = f"http://{host}:{port}"

        self.inventory_provider = InventoryProvider()
        self.planner = NavigationPlanner(self.base_url)
        self.manifest_service = DocumentationMetadataService(language=self.language, theme=self.theme, device=self.device)

        device_str = self.device or 'desktop'
        device_clean = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in device_str)
        self.device_output_dir = os.path.join(SCREENSHOTS_DIR, device_clean)
        self.output_dir = LATEST_SCREENSHOTS_DIR
        self.global_context = {
            "page_id": None,
            "page_title": None,
            "route": None,
            "tab_id": None,
            "tab_order": 0,
            "nested_tab_id": None,
            "nested_tab_order": 0,
            "modal_id": None,
            "modal_order": 0,
            "is_admin": False
        }

    def wait_for_ui_ready(self, page: Page) -> None:
        page.wait_for_load_state('networkidle')
        try:
            page.wait_for_selector('.spinner-overlay', state='hidden', timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(300)

    def wait_for_charts(self, page: Page) -> None:
        page.wait_for_timeout(300)
        page.evaluate("""async () => {
            if (window.Apex) window.Apex.chart = { animations: { enabled: false } };
            window.dispatchEvent(new Event('resize'));
            await new Promise(r => setTimeout(r, 300));
            const elements = document.querySelectorAll('.card, canvas, [id*="chart"], .apexcharts-canvas, .chart-container');
            for (const el of elements) {
                el.scrollIntoView({ behavior: 'auto', block: 'center' });
                await new Promise(r => setTimeout(r, 50));
            }
            window.scrollTo(0, 0);
            const mainContent = document.querySelector('.main-content, #main-wrapper, main, .container-fluid');
            if (mainContent) mainContent.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(800)

