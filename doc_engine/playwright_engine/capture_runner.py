import os
import sys
import time
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from playwright.sync_api import sync_playwright, Page

from doc_engine.config import LATEST_SCREENSHOTS_DIR
from doc_engine.services.inventory_provider import InventoryProvider
from doc_engine.services.navigation_planner import NavigationPlanner, sanitize_filename, safe_filename
from doc_engine.services.documentation_metadata_service import DocumentationMetadataService


logger = logging.getLogger(__name__)

def log(msg: str) -> None:
    """Logs message with format matching capture_pages.js time format."""
    now_str = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{now_str}] {msg}")
    except UnicodeEncodeError:
        safe_msg = msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
        print(f"[{now_str}] {safe_msg}")


def check_cancelled_and_exit(manifest_service: DocumentationMetadataService) -> None:
    if manifest_service.check_cancelled():
        print("\n[!] Cancellation requested. Stopping capture.")
        manifest_service.update_status('cancelled')
        sys.exit(0)


class PythonPlaywrightCaptureEngine:
    """
    Thin, robust Playwright Python automation engine for screenshot generation.
    Receives configuration, inventory, and navigation context from Python services.
    """
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

    def capture_screenshot(self, page: Page, filename: str) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, f"{filename}.png")

        style_handle = page.add_style_tag(content="""
            .modal.show {
              position: absolute !important;
              overflow: visible !important;
              height: auto !important;
              bottom: auto !important;
            }
            .modal-dialog {
              height: auto !important;
              max-height: none !important;
            }
            .modal-content {
              overflow: visible !important;
              height: auto !important;
              max-height: none !important;
            }
            .modal-body {
              overflow: visible !important;
              height: auto !important;
              max-height: none !important;
            }
            body {
              height: auto !important;
              overflow: auto !important;
            }
        """)

        page.wait_for_timeout(200)
        page.screenshot(path=filepath, full_page=True)
        try:
            page.evaluate("(el) => el.remove()", style_handle)
        except Exception:
            pass

        self.manifest_service.record_screenshot(self.global_context, filename)
        log(f"[INFO] Captured: {filename}.png")

    def capture_modal_tabs(self, page: Page, file_prefix: str, close_after: bool = True) -> None:
        is_modal_visible = False
        try:
            page.wait_for_selector('.modal.show', timeout=5000)
            is_modal_visible = True
        except Exception:
            is_modal_visible = False

        if not is_modal_visible:
            log("     Modal did not successfully open. Skipping its tabs.")
            return

        try:
            page.wait_for_selector('.spinner-overlay', state='hidden', timeout=5000)
            page.wait_for_selector('.modal.show .spinner-border, .modal.show .spinner-overlay', state='hidden', timeout=3000)
        except Exception:
            pass

        try:
            page.wait_for_selector(
                '.modal.show .nav-tabs .nav-link, .modal.show .nav-pills .nav-link',
                timeout=1500
            )
        except Exception:
            pass

        tabs = page.evaluate("""() => {
            const tabButtons = Array.from(document.querySelectorAll('.modal.show .nav-tabs .nav-item button, .modal.show .nav-tabs .nav-link, .modal.show .nav-pills .nav-item button, .modal.show .nav-pills .nav-link'));
            const visibleButtons = tabButtons.filter(b => {
              const li = b.closest('li');
              if (li && (li.classList.contains('d-none') || li.style.display === 'none')) return false;
              return true;
            });
            
            return visibleButtons.map((b, i) => {
              if (!b.id) b.id = 'temp-modal-tab-' + i;
              const dataI18n = b.getAttribute('data-i18n');
              const cleanId  = b.id.replace(/[-_]tab$/i, '');
              const filenameKey = dataI18n || cleanId || ('tab_' + i);
              return { id: b.id, name: b.textContent.trim(), filenameKey };
            });
        }""")

        if tabs and len(tabs) > 0:
            self.manifest_service.update_status('running', 'Discovering Tabs...')
            for t in tabs:
                check_cancelled_and_exit(self.manifest_service)
                log(f"        -> Capturing modal tab: {t['name']}")
                page.evaluate("(tabId) => { const btn = document.getElementById(tabId); if (btn) btn.click(); }", t['id'])
                page.wait_for_timeout(200)
                self.global_context["nested_tab_id"] = t['filenameKey']
                self.global_context["nested_tab_order"] = t.get("order", 0)
                self.global_context["page_title"] = t.get("name") or None
                self.capture_screenshot(page, f"{file_prefix}_{sanitize_filename(t['filenameKey'])}")
                self.global_context["nested_tab_id"] = None
                self.global_context["nested_tab_order"] = 0
        else:
            self.capture_screenshot(page, file_prefix)

        if close_after:
            close_btn = page.query_selector('.modal.show .btn-close, .modal.show [data-bs-dismiss="modal"]')
            if close_btn:
                try:
                    close_btn.click(force=True)
                except Exception:
                    page.keyboard.press('Escape')
            else:
                page.keyboard.press('Escape')

            try:
                page.wait_for_selector('.modal.show', state='hidden', timeout=2000)
            except Exception:
                pass

    def process_asset_rows(self, page: Page, route_prefix: str) -> None:
        log('  -> Processing per-type asset modals (View & Edit)...')

        page.evaluate("""async () => {
            let attempts = 0;
            while (attempts < 20) {
                if (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.assets && fixedAssetsState.assets.length > 0) {
                    return true;
                }
                await new Promise(resolve => setTimeout(resolve, 250));
                attempts++;
            }
            return false;
        }""")

        distinct_assets = page.evaluate("""() => {
            const assets = (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.assets) ? fixedAssetsState.assets : [];
            const map = new Map();
            for (const asset of assets) {
                const assetType = asset.asset_type || asset.type || 'Other Assets';
                const isGold = assetType.toLowerCase() === 'gold';
                const purity = isGold ? (asset.gold_details?.purity || asset.purity || '24k') : null;
                if (!map.has(assetType)) {
                    map.set(assetType, { id: asset.id, type: assetType, isGold, purity });
                }
            }
            return Array.from(map.values());
        }""")

        if not distinct_assets or len(distinct_assets) == 0:
            log("     No fixed assets found in the table. Skipping View/Edit per-row capture.")
        else:
            self.manifest_service.update_status('running', 'Discovering Assets...')
            for info in distinct_assets:
                check_cancelled_and_exit(self.manifest_service)
                asset_type = info.get("type", "Other Assets")
                log(f"     -> Selecting View asset type: {asset_type}")


                view_clicked = page.evaluate("""(assetInfo) => {
                    if (assetInfo.isGold) {
                        if (typeof openGoldPurchaseDetails === 'function') {
                            openGoldPurchaseDetails(assetInfo.id, assetInfo.purity || '24k');
                            return true;
                        }
                    } else {
                        if (typeof showFixedAssetDetails === 'function') {
                            showFixedAssetDetails(assetInfo.id);
                            return true;
                        }
                    }
                    return false;
                }""", info)

                if view_clicked:
                    self.capture_modal_tabs(page, f"fixed_assets_assets_view_{sanitize_filename(asset_type.lower())}", close_after=False)
                    page.evaluate("""() => {
                        if (typeof clearGoldPurityReturnContext === 'function') clearGoldPurityReturnContext();
                        const closeBtn = document.querySelector('.modal.show .btn-close');
                        if (closeBtn) closeBtn.click();
                    }""")
                    try:
                        page.wait_for_selector('.modal.show', state='hidden', timeout=2000)
                    except Exception:
                        pass

                log(f"     -> Selecting Edit asset type: {asset_type}")
                edit_clicked = page.evaluate("""(assetInfo) => {
                    if (assetInfo.isGold) {
                        if (typeof openGoldPurchaseEditor === 'function') {
                            openGoldPurchaseEditor(assetInfo.id, assetInfo.purity || '24k');
                            return true;
                        }
                    } else {
                        if (typeof showFixedAssetModal === 'function') {
                            showFixedAssetModal(assetInfo.id);
                            return true;
                        }
                    }
                    return false;
                }""", info)

                if edit_clicked:
                    self.capture_modal_tabs(page, f"fixed_assets_assets_edit_{sanitize_filename(asset_type.lower())}", close_after=False)
                    page.evaluate("""() => {
                        if (typeof clearGoldPurityReturnContext === 'function') clearGoldPurityReturnContext();
                        const closeBtn = document.querySelector('.modal.show .btn-close');
                        if (closeBtn) closeBtn.click();
                    }""")
                    try:
                        page.wait_for_selector('.modal.show', state='hidden', timeout=2000)
                    except Exception:
                        pass

        log('  -> Processing Add New Asset modal combinations...')
        try:
            add_btn_clicked = page.evaluate("""() => {
                const btn = document.querySelector('button[onclick*="showFixedAssetModal"]');
                if (btn) { btn.click(); return true; }
                return false;
            }""")

            if add_btn_clicked:
                is_modal_visible = False
                try:
                    page.wait_for_selector('.modal.show', timeout=5000)
                    is_modal_visible = True
                except Exception:
                    is_modal_visible = False

                if is_modal_visible:
                    asset_types = page.evaluate("""() => {
                        const select = document.querySelector('select#fa_type');
                        if (!select) return [];
                        return Array.from(select.options)
                            .filter(opt => opt.value)
                            .map(opt => ({ value: opt.value, text: opt.textContent.trim() }));
                    }""")

                    for t_info in asset_types:
                        check_cancelled_and_exit(self.manifest_service)
                        log(f"     -> Selecting Add asset type: {t_info['text']}")
                        page.evaluate("""() => {
                            const generalTab = document.getElementById('general-tab');
                            if (generalTab) generalTab.click();
                        }""")
                        page.wait_for_timeout(500)

                        page.select_option('select#fa_type', t_info['value'])
                        page.evaluate("""() => {
                            const select = document.querySelector('select#fa_type');
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                        }""")
                        page.wait_for_timeout(500)

                        type_filename = sanitize_filename(t_info['value'])
                        self.capture_modal_tabs(page, f"{route_prefix}_add_{type_filename}", close_after=False)

                    close_btn = page.query_selector('.modal.show .btn-close, .modal.show [data-bs-dismiss="modal"]')
                    if close_btn:
                        page.evaluate("""() => {
                            if (typeof clearGoldPurityReturnContext === 'function') clearGoldPurityReturnContext();
                        }""")
                        close_btn.click(force=True)
                    else:
                        page.keyboard.press('Escape')
                    try:
                        page.wait_for_selector('.modal.show', state='hidden', timeout=2000)
                    except Exception:
                        pass
                else:
                    log("     Add Asset modal did not visibly open.")
        except Exception as e:
            log(f"     Failed to process Add New Asset: {e}")

    def click_tab_by_id(self, page: Page, tab: Dict[str, Any]) -> bool:
        return page.evaluate("""(tabData) => {
            let target = null;
            if (tabData.id) {
                const candidates = Array.from(document.querySelectorAll(`[onclick*="${tabData.id}"], [data-bs-target*="${tabData.id}"]`));
                target = candidates.find(el => !el.closest('#sidebar'));
                if (!target) {
                    const byId = document.getElementById(tabData.id + '-tab') || document.getElementById(tabData.id);
                    if (byId && !byId.closest('#sidebar')) target = byId;
                }
            }
            if (!target) {
                const elements = Array.from(document.querySelectorAll('button, .nav-link, .nav-item, [role="tab"], .dropdown-item, .wf-dropdown-item'));
                const normalize = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
                const normText = normalize(tabData.name);
                let matches = elements.filter(el => !el.closest('#sidebar') && !el.classList.contains('dropdown-toggle'));
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

    def process_modals(self, page: Page, route_prefix: str, modals: List[Dict[str, Any]]) -> None:
        for modal in modals:
            check_cancelled_and_exit(self.manifest_service)
            try:
                log(f"  -> Opening modal: {modal['name']}")
                clicked = page.evaluate("""(modal) => {
                    const modalName = modal.name;
                    const trigger = modal.trigger;
                    const buttons = Array.from(document.querySelectorAll('button, a'));
                    const safeButtons = buttons.filter(b => !b.closest('#sidebar'));
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
                self.global_context["modal_id"] = None
                self.global_context["modal_order"] = 0
            except Exception as err:
                log(f"  Failed processing modal {modal['name']}: {err}")

    def execute_with_retry(self, action_name: str, action_fn) -> Any:
        try:
            return action_fn()
        except Exception as err:
            log(f"Retry 1 for {action_name} due to error: {err}")
            time.sleep(2.0)
            return action_fn()

    def perform_login(self, page: Page) -> None:
        log("Capturing Auth Pages...")
        self.global_context["page_id"] = "auth"
        self.global_context["route"] = "auth"

        page.goto(f"{self.base_url}/accounts/signup/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "create_account"
        self.global_context["page_title"] = "Create Account"
        self.capture_screenshot(page, "create_account")

        page.goto(f"{self.base_url}/accounts/forgot-password/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "forgot_password"
        self.global_context["page_title"] = "Forgot Password"
        self.capture_screenshot(page, "forgot_password")

        page.goto(f"{self.base_url}/accounts/login/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "login"
        self.global_context["page_title"] = "Login"
        self.capture_screenshot(page, "login")

        self.global_context["tab_id"] = None
        self.global_context["route"] = None
        self.global_context["page_id"] = None

        log(f"Logging in at {self.base_url}...")
        page.fill('input[name="username"], input[type="email"]', self.username)
        page.fill('input[name="password"], input[type="password"]', self.password)
        page.click('button[type="submit"], input[type="submit"], .btn-login')
        self.wait_for_ui_ready(page)

    def inject_dynamic_routes(self, page: Page, inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        companies = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('button.nav-item[data-route^="salary-"]'));
            return links.map(link => ({
                name: link.textContent.trim(),
                id: link.getAttribute('data-route').replace('salary-', ''),
                route: link.getAttribute('data-route')
            }));
        }""")

        if companies and len(companies) > 0:
            log(f"Discovered {len(companies)} companies for Salary routes.")
            salary_routes = []
            for i, c in enumerate(companies):
                nested = []
                if i == len(companies) - 1:
                    nested.append({"name": "Add Salary Entry", "type": "modal", "trigger": f"eval:showSalaryModal(null, {c['id']})"})
                    nested.append({"name": "Add Perdiem1", "type": "modal", "trigger": f"eval:showPerDiemListModal({c['id']})"})
                    nested.append({"name": "Add Perdiem2", "type": "modal", "trigger": f"eval:showPerDiemFormModal(null, {c['id']}, new Date().getFullYear())"})

                salary_routes.append({
                    "route": c['route'],
                    "title": f"Salary_{sanitize_filename(c['name'].lower())}",
                    "customPrefix": f"salary_{i + 1}",
                    "nested_navigation": nested
                })

            salary_routes.append({
                "route": "all-companies",
                "title": "All Companies",
                "nested_navigation": [{"name": "Add Company", "type": "modal", "trigger": "showCompanyModal"}]
            })

            target_index = -1
            for idx, item in enumerate(inventory):
                if item.get("route") == "financial-advisor":
                    target_index = idx
                    break

            if target_index != -1:
                for sr in reversed(salary_routes):
                    inventory.insert(target_index + 1, sr)
            else:
                inventory.extend(salary_routes)

        return inventory

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

        full_url = self.planner.get_full_url(route)
        page.goto(full_url)
        self.wait_for_ui_ready(page)
        if self.planner.is_chart_route(route):
            self.wait_for_charts(page)

        tabs = item.get("tabs", [])
        nested_nav = item.get("nested_navigation", [])

        if tabs and len(tabs) > 0:
            for tab in tabs:
                check_cancelled_and_exit(self.manifest_service)
                self.manifest_service.current_progress += 1
                self.manifest_service.update_status('running', title, tab.get("name", ""))

                def capture_tab_action():
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

                    if route == 'fixed-assets' and tab_id == 'assets':
                        self.process_asset_rows(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}")
                    elif tab.get("nested_navigation"):
                        self.process_modals(page, f"{route_prefix}_{safe_filename(tab_name, tab_id)}", tab.get("nested_navigation"))

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

            try:
                self.execute_with_retry(f"page {title}", capture_page_action)
            except Exception as err:
                log(f"  Failed to capture page {title}: {err}")

    def run(self) -> bool:
        log('Starting screenshot generation...')
        log(f'[CONFIG] Theme: {self.theme.upper()} | Language: {self.language.upper()}')
        if self.device:
            log(f'[CONFIG] Device: {self.device}')
        log(f'[CONFIG] Output folder: {self.output_dir}')

        log('Cleaning up old screenshots...')
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)

        context_opts, launch_args = self.inventory_provider.resolve_device_config(self.device)

        with sync_playwright() as p:
            pw_device_name = context_opts.pop("playwright_device", None)
            if pw_device_name and pw_device_name in p.devices:
                context_opts.update(p.devices[pw_device_name])
                launch_args = []

            if context_opts.get("viewport") is None:
                context_opts.pop("viewport", None)
                context_opts["no_viewport"] = True

            browser = p.chromium.launch(headless=False, args=launch_args)
            context = browser.new_context(**context_opts)
            page = context.new_page()


            init_js = f"""
                const cfg = {{ theme: '{self.theme}', language: '{self.language}' }};
                window.Apex = {{ chart: {{ animations: {{ enabled: false }} }} }};
                const existingChart = window.Chart;
                if (existingChart && existingChart.defaults) {{
                    existingChart.defaults.animation = false;
                    if (existingChart.defaults.plugins && existingChart.defaults.plugins.tooltip) {{
                        existingChart.defaults.plugins.tooltip.animation = false;
                    }}
                }}
                let _chart = existingChart;
                Object.defineProperty(window, 'Chart', {{
                    configurable: true,
                    get() {{ return _chart; }},
                    set(val) {{
                        _chart = val;
                        if (val && val.defaults) {{
                            val.defaults.animation = false;
                            val.defaults.responsiveAnimationDuration = 0;
                            if (val.defaults.plugins && val.defaults.plugins.tooltip) {{
                                val.defaults.plugins.tooltip.animation = false;
                            }}
                        }}
                    }}
                }});
                localStorage.setItem('theme', cfg.theme);
                localStorage.setItem('lang', cfg.language);
                if (cfg.theme === 'light') {{
                    document.documentElement.setAttribute('data-theme', 'light');
                }} else {{
                    document.documentElement.removeAttribute('data-theme');
                }}
            """
            page.add_init_script(script=init_js)


            failed_pages = []
            try:
                page.goto(f"{self.base_url}/accounts/login/")
                page.evaluate("""() => { localStorage.clear(); sessionStorage.clear(); }""")
                context.clear_cookies()
                log('[INFO] Browser storage cleared. Starting fresh...')

                self.perform_login(page)
                raw_inventory = self.inventory_provider.get_page_inventory()
                inventory = self.inject_dynamic_routes(page, raw_inventory)

                for item in inventory:
                    check_cancelled_and_exit(self.manifest_service)
                    route = item.get("route", "")
                    title = item.get("title", "")
                    self.global_context["page_id"] = sanitize_filename(route.replace('/', '')) or sanitize_filename(title)
                    self.global_context["route"] = route
                    self.global_context["page_title"] = title
                    self.global_context["is_admin"] = item.get("is_admin") is True
                    self.global_context["tab_order"] += 1

                    try:
                        self.process_page(page, item)
                    except Exception as err:
                        log(f"Fatal error processing page {route}: {err}")
                        failed_pages.append({"route": route, "error": str(err)})
                        err_str = str(err).lower()
                        if "browser has been closed" in err_str or "target page, context or browser has been closed" in err_str:
                            log("Browser was manually closed. Aborting capture.")
                            self.manifest_service.update_status('cancelled', '', '', 'Browser was manually closed.')
                            sys.exit(1)

                self.manifest_service.failed_pages = failed_pages
                if len(failed_pages) > 0:
                    log('\n--- Capture Completed with Failures ---')
                    log(str(failed_pages))
                    self.manifest_service.total_items = self.manifest_service.screenshots_count
                    self.manifest_service.update_status('failed', 'Completed with failures', '', f"{len(failed_pages)} pages failed")
                    return False
                else:
                    log('\n--- Capture Completed Successfully ---')
                    self.manifest_service.total_items = self.manifest_service.screenshots_count
                    self.manifest_service.update_status('finished')
                    self.manifest_service.save_manifest_and_metadata()
                    log('[INFO] Saved manifest.json and capture_metadata.json')
                    return True

            except Exception as err:
                log(f"Fatal error during execution: {err}")
                if "cancelled" in str(err).lower():
                    sys.exit(2)
                sys.exit(1)
            finally:
                try:
                    page.evaluate("""() => { localStorage.clear(); sessionStorage.clear(); }""")
                    context.clear_cookies()
                    log('[INFO] Browser storage cleared after run.')
                except Exception:
                    pass
                browser.close()
                log('Screenshot generation complete.')


def run_python_capture(host: str = '127.0.0.1', port: str = '8001',
                       username: str = 'eehab_said', password: str = 'Eehabdev1',
                       theme: str = 'dark', language: str = 'en', device: Optional[str] = None) -> bool:
    """Entry point function to invoke Python Playwright capture engine."""
    engine = PythonPlaywrightCaptureEngine(
        host=host, port=port, username=username, password=password,
        theme=theme, language=language, device=device
    )
    return engine.run()
