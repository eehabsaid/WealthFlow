"""Deterministic first-load helper for the real-browser AI tests.

The app decides after boot, from /api/onboarding/status/, whether the first-run
wizard opens on top of the page. The old helpers guessed with a fixed wait for
the "Skip for now" button; on a slow machine the wizard could open after the
guess, and the test then raced it. This waits for the app's own answer instead,
then for the real end state (no dialog or backdrop left on the page)."""

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
    with page.expect_response(lambda r: STATUS_URL in r.url, timeout=BOOT_TIMEOUT_MS) as waiting:
        page.goto(url)
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
