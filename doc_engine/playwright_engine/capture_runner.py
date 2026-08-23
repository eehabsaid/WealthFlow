import os
import sys
import time
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from playwright.sync_api import sync_playwright, Page

from doc_engine.config import LATEST_SCREENSHOTS_DIR, SCREENSHOTS_DIR
from doc_engine.services.inventory_provider import InventoryProvider
from doc_engine.services.navigation_planner import NavigationPlanner, sanitize_filename, safe_filename
from doc_engine.services.documentation_metadata_service import DocumentationMetadataService


logger = logging.getLogger(__name__)

# Configurable browser visibility mode:
# 1 = Environment-controlled mode (Default: headless unless WF_DOC_ENGINE_HEADED=1)
# 0 = Force old behavior (always headed/visible browser window, headless=False)
USE_ENV_HEADLESS_CONFIG = 0

# Local vendored copies of the app's external CDN dependencies
# (bootstrap.bundle.min.js, chart.umd.js, leaflet.js/css, bootstrap CSS/icons).
# Some server/CI/sandboxed network environments block or cannot reach
# cdn.jsdelivr.net, cdnjs.cloudflare.com, or unpkg.com (confirmed: this
# occurs in at least one real environment used to run this capture engine,
# manifesting as "bootstrap is not defined" / "Chart is not a constructor"
# and cascading into modal-open failures across many pages). Serving these
# exact, pinned-version files locally via request interception makes capture
# reliable regardless of the network's CDN reachability, without changing
# what the app itself serves to real users.
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor", "assets")

_CDN_LOCAL_MAP = {
    "bootstrap.bundle.min.js": "bootstrap.bundle.min.js",
    "bootstrap.min.css": "bootstrap.min.css",
    "bootstrap-icons.css": "bootstrap-icons.css",
    "bootstrap-icons.woff2": "fonts/bootstrap-icons.woff2",
    "bootstrap-icons.woff": "fonts/bootstrap-icons.woff",
    "chart.umd.min.js": "chart.umd.js",
    "chart.umd.js": "chart.umd.js",
    "leaflet.js": "leaflet.js",
    "leaflet.css": "leaflet.css",
}


def _install_cdn_fallback(page: Page) -> None:
    """Intercepts known CDN requests and serves a local vendored copy if the
    real network request would otherwise be blocked/unreachable. Falls back
    to the real network for anything not recognized, so this only changes
    behavior for the specific libraries known to sometimes fail here."""
    def handle_route(route):
        url = route.request.url
        for cdn_name, local_name in _CDN_LOCAL_MAP.items():
            if cdn_name in url:
                local_path = os.path.join(_VENDOR_DIR, local_name)
                if os.path.isfile(local_path):
                    route.fulfill(path=local_path)
                    return
        route.continue_()

    page.route("https://cdn.jsdelivr.net/**", handle_route)
    page.route("https://cdnjs.cloudflare.com/**", handle_route)
    page.route("https://unpkg.com/**", handle_route)


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

    def capture_screenshot(self, page: Page, filename: str) -> None:
        check_cancelled_and_exit(self.manifest_service)
        os.makedirs(self.device_output_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        filepath_device = os.path.join(self.device_output_dir, f"{filename}.png")
        filepath_latest = os.path.join(self.output_dir, f"{filename}.png")

        style_handle = page.add_style_tag(content="""
            html, body {
              min-width: 1920px !important;
              width: 100% !important;
              height: auto !important;
              overflow: auto !important;
            }
            #main-content, #main-content > div, #settingsContent, .container, .container-fluid, .page-header, .wf-tabs-shell {
              max-width: 100% !important;
              width: 100% !important;
            }
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
        """)



        page.wait_for_timeout(200)
        page.screenshot(path=filepath_device, full_page=True)
        try:
            shutil.copy2(filepath_device, filepath_latest)
        except Exception as e:
            log(f"[WARNING] Could not copy screenshot to latest folder: {e}")

        try:
            page.evaluate("(el) => el.remove()", style_handle)
        except Exception:
            pass

        self.manifest_service.record_screenshot(self.global_context, filename)
        log(f"[INFO] Captured: {filename}.png")

    def ensure_modals_closed(self, page: Page) -> None:
        """
        Forcefully clears return context, hides all visible modals, and
        removes lingering backdrops.

        IMPORTANT: also DISPOSES each Bootstrap modal instance after hiding
        it, not just hiding it. The app shares a single reusable modal
        container (#globalModal, see static/js/app/modals.js) across ~30
        different features (Fixed Assets Add/Edit/View, most AI Workspace
        modals, Bank Certificates, Balance, Expenses, Reminders, etc.) - the
        SAME Bootstrap.Modal JS instance is reused every time, just with its
        inner HTML swapped out. Bootstrap's own .show() call silently does
        nothing if it thinks the instance is still mid-hide-transition, so
        force-hiding via class/style changes alone (without disposing) can
        leave the instance in a state where the VERY NEXT modal opened
        immediately after this one closes never actually appears - it fails
        silently and the capture times out with no error. Disposing here
        guarantees every subsequent showModal() call gets a clean instance,
        regardless of timing between consecutive modal captures.
        """
        try:
            page.evaluate("""() => {
                if (typeof clearGoldPurityReturnContext === 'function') {
                    clearGoldPurityReturnContext();
                }
                if (typeof goldPurityReturnContext !== 'undefined') {
                    goldPurityReturnContext = null;
                }
                const openModals = document.querySelectorAll('.modal.show, .modal[style*="display: block"]');
                openModals.forEach(m => {
                    if (window.bootstrap && window.bootstrap.Modal) {
                        const inst = window.bootstrap.Modal.getInstance(m);
                        if (inst) {
                            try { inst.hide(); } catch(e) {}
                            try { inst.dispose(); } catch(e) {}
                        }
                    }
                    m.classList.remove('show');
                    m.style.display = 'none';
                    m.setAttribute('aria-hidden', 'true');
                });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('padding-right');
                document.body.style.removeProperty('overflow');
            }""")
            page.wait_for_selector('.modal.show', state='hidden', timeout=1000)
        except Exception:
            pass

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
        # Order matches the actual page layout, top to bottom: the "Add New
        # Asset" button sits above the table, so its modal is captured first;
        # per-row View/Edit actions (further down the page, one per existing
        # row) are captured second. This keeps generated docs in the same
        # visual order a user encounters them in the app.
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
                        self.global_context["modal_id"] = f"add_{type_filename}"
                        self.capture_modal_tabs(page, f"{route_prefix}_add_{type_filename}", close_after=False)
                        self.global_context["modal_id"] = None

                    self.ensure_modals_closed(page)
                else:
                    log("     Add Asset modal did not visibly open.")
        except Exception as e:
            log(f"     Failed to process Add New Asset: {e}")
        finally:
            self.ensure_modals_closed(page)

        log('  -> Processing per-type asset modals (View & Edit)...')

        page.evaluate("""async () => {
            if (typeof fixedAssetsState !== 'undefined' && fixedAssetsState.loadAssets && (!fixedAssetsState.assets || fixedAssetsState.assets.length === 0)) {
                try { await fixedAssetsState.loadAssets(); } catch(e) {}
            }
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

        distinct_assets = page.evaluate(r"""() => {
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
            if (map.size === 0) {
                const rows = Array.from(document.querySelectorAll('#assets-table tbody tr, .table tbody tr'));
                rows.forEach((tr, i) => {
                    const editBtn = tr.querySelector('button[onclick*="showFixedAssetModal"], button[onclick*="openGold"]');
                    const viewBtn = tr.querySelector('button[onclick*="showFixedAssetDetails"], button[onclick*="showGold"]');
                    const typeTd = tr.querySelector('td:nth-child(2)');
                    const assetType = typeTd ? typeTd.textContent.trim() : ('AssetType_' + i);
                    const isGold = assetType.toLowerCase() === 'gold';
                    if (editBtn || viewBtn) {
                        const onclick = (editBtn || viewBtn).getAttribute('onclick') || '';
                        const idMatch = onclick.match(/\((\d+)/);
                        const id = idMatch ? parseInt(idMatch[1], 10) : (i + 1);
                        if (!map.has(assetType)) {
                            map.set(assetType, { id, type: assetType, isGold, purity: isGold ? '24k' : null });
                        }
                    }
                });
            }
            return Array.from(map.values());
        }""")

        if not distinct_assets or len(distinct_assets) == 0:
            log("     No fixed assets found in the table. Skipping View/Edit per-row capture.")
            return

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
                self.global_context["modal_id"] = f"view_{sanitize_filename(asset_type.lower())}"
                self.capture_modal_tabs(page, f"fixed_assets_assets_view_{sanitize_filename(asset_type.lower())}", close_after=False)
                self.global_context["modal_id"] = None
                self.ensure_modals_closed(page)

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
                self.global_context["modal_id"] = f"edit_{sanitize_filename(asset_type.lower())}"
                self.capture_modal_tabs(page, f"fixed_assets_assets_edit_{sanitize_filename(asset_type.lower())}", close_after=False)
                self.global_context["modal_id"] = None
                self.ensure_modals_closed(page)

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


    def inject_dynamic_routes(self, page: Page, inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        companies = page.evaluate("""async () => {
            if (window._companies && window._companies.length > 0) {
                return window._companies.map(c => ({
                    name: c.display_name || c.name,
                    id: String(c.id),
                    route: `employment-${c.id}`
                }));
            }
            try {
                const res = await fetch('/api/companies/');
                const data = await res.json();
                const comps = data.companies || [];
                if (comps.length > 0) {
                    return comps.map(c => ({
                        name: c.display_name || c.name,
                        id: String(c.id),
                        route: `employment-${c.id}`
                    }));
                }
            } catch (e) {}
            const links = Array.from(document.querySelectorAll('.employer-tab, [data-employer-id], button.nav-item[data-route^="employment-"], button.nav-item[data-route^="salary-"]'));
            return links.map(link => {
                const cId = link.getAttribute('data-employer-id') || (link.getAttribute('data-route') || '').replace(/^(salary|employment)-/, '');
                return {
                    name: link.textContent.trim(),
                    id: String(cId),
                    route: `employment-${cId}`
                };
            });
        }""")

        if companies and len(companies) > 0:
            log(f"Discovered {len(companies)} companies for Employment tabs.")
            emp_tabs = []
            for i, c in enumerate(companies):
                nested = []
                if i == len(companies) - 1:
                    nested = [
                        {"name": "Add Salary Entry", "type": "modal", "trigger": f"eval:showSalaryModal(null, {c['id']})"},
                        {"name": "Edit Salary Entry", "type": "modal", "trigger": f"eval:const btn = document.querySelector('.btn-icon[onclick*=\"showSalaryModal\"], button[onclick*=\"showSalaryModal\"]'); if(btn) btn.click(); else showSalaryModal(null, {c['id']});"},
                        {"name": "Per Diem List", "type": "modal", "trigger": f"eval:showPerDiemListModal({c['id']})"},
                        {"name": "Add Per Diem", "type": "modal", "trigger": f"eval:showPerDiemFormModal(null, {c['id']}, new Date().getFullYear())"}
                    ]

                emp_tabs.append({
                    "name": c['name'],
                    "id": str(c['id']),
                    "nested_navigation": nested
                })

            emp_item = None
            for item in inventory:
                if item.get("route") == "employment":
                    emp_item = item
                    break

            if emp_item:
                emp_item["tabs"] = emp_tabs
            else:
                target_index = -1
                for idx, item in enumerate(inventory):
                    if item.get("route") == "financial-advisor":
                        target_index = idx
                        break

                new_entry = {
                    "route": "employment",
                    "title": "Employment",
                    "tabs": emp_tabs
                }
                if target_index != -1:
                    inventory.insert(target_index + 1, new_entry)
                else:
                    inventory.append(new_entry)

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

    def run(self) -> bool:
        log('Starting screenshot generation...')
        log(f'[CONFIG] Theme: {self.theme.upper()} | Language: {self.language.upper()}')
        if self.device:
            log(f'[CONFIG] Device: {self.device}')
        log(f'[CONFIG] Device Output Folder: {self.device_output_dir}')
        log(f'[CONFIG] Latest Output Folder: {self.output_dir}')

        log(f'Cleaning up old screenshots for device {self.device or "desktop"}...')
        if os.path.exists(self.device_output_dir):
            shutil.rmtree(self.device_output_dir, ignore_errors=True)
        os.makedirs(self.device_output_dir, exist_ok=True)

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

            # headless=False requires a real display (X server). On any
            # server/CI/sandboxed environment without one, Playwright hangs
            # or crashes with "Missing X server or $DISPLAY". Default to
            # headless so this runs reliably everywhere; allow opting into
            # a visible browser window only when explicitly requested for
            # local debugging via WF_DOC_ENGINE_HEADED=1.
            if USE_ENV_HEADLESS_CONFIG == 1:
                run_headed = os.environ.get("WF_DOC_ENGINE_HEADED", "").strip() == "1"
                browser = p.chromium.launch(headless=not run_headed, args=launch_args)
            else:
                browser = p.chromium.launch(headless=False, args=launch_args)

            context = browser.new_context(**context_opts)
            page = context.new_page()
            _install_cdn_fallback(page)

            # Diagnostic: surface real browser-side JS errors/warnings during
            # capture. Modal-open failures were previously silent - this
            # makes the actual root cause visible in the log instead of just
            # "Modal did not successfully open."
            page.on("console", lambda msg: log(f"     [browser:{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
            page.on("pageerror", lambda exc: log(f"     [browser:pageerror] {exc}\n{getattr(exc, 'stack', '')}"))



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
                // Guard: add_init_script can fire before document.documentElement
                // is guaranteed available (e.g. very early in a fresh navigation,
                // on about:blank before the real page has committed). Without this
                // guard, this fires a real, reproducible "Cannot read properties
                // of null (reading 'removeAttribute')" error on every single page
                // navigation during capture.
                function _applyThemeAttr() {{
                    if (!document.documentElement) return;
                    if (cfg.theme === 'light') {{
                        document.documentElement.setAttribute('data-theme', 'light');
                    }} else {{
                        document.documentElement.removeAttribute('data-theme');
                    }}
                }}
                if (document.documentElement) {{
                    _applyThemeAttr();
                }} else {{
                    document.addEventListener('DOMContentLoaded', _applyThemeAttr, {{ once: true }});
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

                # Safety net: compare the LIVE sidebar against inventory.json
                # and append any page not already declared. Declared routes
                # (and their hand-tuned tabs/nested_navigation) are never
                # touched or reordered - this only fills gaps, so a page
                # added to the sidebar in the future is still captured even
                # if nobody remembers to update inventory.json.
                discovered_routes = self.discover_sidebar_routes(page)
                if discovered_routes:
                    inventory = self.merge_discovered_routes(inventory, discovered_routes)

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
