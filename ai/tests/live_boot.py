"""Deterministic first-load helper for the real-browser AI tests.

The app decides after boot, from /api/onboarding/status/, whether the first-run
wizard opens on top of the page. The old helpers guessed with a fixed wait for
the "Skip for now" button; on a slow machine the wizard could open after the
guess, and the test then raced it. This waits for the app's own answer instead,
then for the real end state (no dialog or backdrop left on the page)."""

import os
import warnings

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

STATUS_URL = "/api/onboarding/status/"
BOOT_TIMEOUT_MS = 60000
DIALOG_TIMEOUT_MS = 30000
UNKNOWN_STATUS_WAIT_MS = 15000
NO_DIALOG_JS = "() => !document.querySelector('.modal.show, .modal-backdrop')"


def _status_of(response):
    """The status payload, or {} when the body is not JSON (the reason is reported on stderr)."""
    try:
        return response.json()
    except Exception:  # noqa: BLE001 - diagnostics only
        try:
            head = response.text()[:200]
        except Exception:  # noqa: BLE001
            head = "<unreadable>"
        warnings.warn(f"{STATUS_URL} gave a non-JSON answer (HTTP {response.status}): {head!r}", stacklevel=2)
        return {}


def first_load(page, url):
    """Open `url` (a fresh page) and return once the app has booted and any first-run wizard is skipped."""
    # Not the default 30 s / "load": on a loaded box the single-threaded live server needs longer to serve every asset.
    # The real boot signals are awaited below (the app's own status answer, then no dialog left on the page).
    with page.expect_response(lambda r: STATUS_URL in r.url, timeout=BOOT_TIMEOUT_MS) as waiting:
        page.goto(url, wait_until="domcontentloaded", timeout=BOOT_TIMEOUT_MS)
    status = _status_of(waiting.value)
    if status.get("needs_wizard") is not False:  # True, or unknown when the answer was unreadable
        skip = page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=DIALOG_TIMEOUT_MS if status else UNKNOWN_STATUS_WAIT_MS)
        except PlaywrightTimeoutError:
            if status:
                raise
        else:
            skip.click()
            page.wait_for_selector("#globalModal.show", state="detached", timeout=DIALOG_TIMEOUT_MS)
    page.wait_for_function(NO_DIALOG_JS, timeout=DIALOG_TIMEOUT_MS)
    return status


WAIT_TIMEOUT_MS = 90000   # a loaded 1-core CI box needs well over the old 30 s for the first AI Advisor render


def scale_timeouts(context):
    """Raise Playwright's per-action and navigation defaults (30 s) to the loaded-box budget for this context."""
    ms = int(os.environ.get("WF_LIVE_WAIT_MS", WAIT_TIMEOUT_MS))
    context.set_default_timeout(ms)
    context.set_default_navigation_timeout(ms)


class PageDiagnostics:
    """Console errors, page errors and still-pending/failed requests of one page, for failure reports."""

    def __init__(self, page):
        self.page, self.console, self.errors, self.failed, self.pending = page, [], [], [], {}
        page.on("console", lambda m: self.console.append(f"{m.type}: {m.text[:200]}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: self.errors.append(str(e)[:300]))
        page.on("request", lambda r: self.pending.__setitem__(r, r.url))
        page.on("requestfinished", lambda r: self.pending.pop(r, None))
        page.on("requestfailed", lambda r: (self.pending.pop(r, None), self.failed.append(f"{r.url} {r.failure}")))

    def report(self, selector):
        try:
            dom = self.page.evaluate(
                "(sel) => ({url: location.href, ready: document.readyState, matches: document.querySelectorAll(sel).length,"
                " body: (document.querySelector(sel.split(' ')[0]) || {}).outerHTML?.slice(0, 300) || null,"
                " dialogs: document.querySelectorAll('.modal.show').length})", selector)
        except Exception as exc:  # noqa: BLE001 - the page may be gone
            dom = {"evaluate_failed": str(exc)[:200]}
        return (f"timeout waiting for {selector!r}\n dom={dom}\n pending={list(self.pending.values())[:10]}\n"
                f" failed={self.failed[:10]}\n page_errors={self.errors[:10]}\n console={self.console[-10:]}")


def wait_for_rows(page, diagnostics, selector, timeout=None):
    """wait_for_selector that, on timeout, fails with what the page was doing (the cause), not just a bare timeout."""
    timeout = timeout or int(os.environ.get("WF_LIVE_WAIT_MS", WAIT_TIMEOUT_MS))   # env knob: reproduce/tune on a box
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except PlaywrightTimeoutError as exc:
        raise AssertionError(diagnostics.report(selector)) from exc
