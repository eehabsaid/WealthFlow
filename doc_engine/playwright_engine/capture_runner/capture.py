"""CaptureMixin: screenshot capture and modal-close/modal-tab handling. See
this package's __init__.py for the sibling list and composition conventions."""
import os
import shutil

from playwright.sync_api import Page

from doc_engine.services.navigation_planner import sanitize_filename
from .helpers import log, check_cancelled_and_exit


class CaptureMixin:
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

