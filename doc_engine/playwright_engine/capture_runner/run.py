"""RunMixin: top-level browser lifecycle and capture-run orchestration.
See this package's __init__.py for the sibling list and composition
conventions."""
import os
import sys
import shutil

from playwright.sync_api import sync_playwright

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log, check_cancelled_and_exit, _install_cdn_fallback, USE_ENV_HEADLESS_CONFIG


class RunMixin:
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


