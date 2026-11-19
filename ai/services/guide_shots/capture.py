"""Headless Chromium, logged in as the guide's user, one JPEG per screen / tab. Runs in its own thread (Playwright's sync API
refuses to start inside a running event loop)."""

from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse

from ai.services.guide_shots.blur import BLUR_JS

logger = logging.getLogger("ai.guide_shots")
VIEWPORT = {"width": 1366, "height": 800}
PAGE_TIMEOUT_MS = 20000

CLICK_TAB_JS = r"""(tab) => {
  const main = document.getElementById('main-content');
  if (!main) return false;
  let target = null;
  if (tab.id) {
    const found = Array.from(main.querySelectorAll(`[onclick*="${tab.id}"], [data-bs-target*="${tab.id}"]`));
    target = found.find(el => el.offsetParent !== null && !el.closest('.d-none')) || main.querySelector('#' + tab.id + '-tab, #' + tab.id);
  }
  if (!target) {
    const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
    const items = Array.from(main.querySelectorAll('button, .nav-link, .nav-item, [role="tab"], .wf-tab')).filter(el => el.offsetParent !== null);
    target = items.find(el => norm(el.textContent) === norm(tab.name));
  }
  if (!target) return false;
  if ((target.hasAttribute('data-bs-toggle') || target.hasAttribute('data-bs-target')) && window.bootstrap && window.bootstrap.Tab)
    window.bootstrap.Tab.getOrCreateInstance(target).show();
  else target.click();
  return true;
}"""


def _settle(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT_MS)
        page.wait_for_selector(".spinner-overlay", state="hidden", timeout=3000)
    except Exception:   # noqa: BLE001 - a page that never goes idle is photographed as it is
        pass
    page.wait_for_timeout(900)


def _shot(page, blurred: bool) -> bytes:
    if page.query_selector("#main-content") is None:   # a login page or an error page is not a screen of the app
        raise RuntimeError("the app screen did not load")
    page.evaluate("window.scrollTo(0, 0)")
    if blurred:
        page.evaluate(BLUR_JS)
    return page.screenshot(type="jpeg", quality=72)


def _run(origin: str, cookie: dict, targets: list[dict], blurred: bool, deadline: float, out: dict) -> None:
    from playwright.sync_api import sync_playwright

    host = urlparse(origin)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, locale="en-US")
            ctx.add_cookies([{**cookie, "domain": host.hostname, "path": "/", "secure": host.scheme == "https", "httpOnly": True}])
            page = ctx.new_page()
            page.set_default_timeout(PAGE_TIMEOUT_MS)
            last_route = None
            for t in targets:
                if time.monotonic() > deadline:
                    break
                try:
                    if t["route"] != last_route:
                        page.goto(origin.rstrip("/") + ("/" if t["route"] == "dashboard" else f"/#{t['route']}"))
                        _settle(page)
                        last_route = t["route"]
                    if t["tab"] and not page.evaluate(CLICK_TAB_JS, t["tab"]):
                        continue
                    if t["tab"]:
                        _settle(page)
                    out[t["key"]] = _shot(page, blurred)
                except Exception as err:   # noqa: BLE001 - one page failing leaves a hole, not a failed guide
                    logger.warning("guide screenshot failed for %s: %s", t["route"], err)
                    last_route = None
        finally:
            browser.close()


def capture(origin: str, cookie: dict, targets: list[dict], blurred: bool, budget_s: float) -> dict[str, bytes]:
    """{key: jpeg bytes} for the pages that could be photographed within budget_s."""
    out: dict[str, bytes] = {}
    worker = threading.Thread(target=_safe, args=(origin, cookie, targets, blurred, time.monotonic() + budget_s, out), daemon=True)
    worker.start()
    worker.join(budget_s + 30)
    return dict(out)


def _safe(*args) -> None:
    try:
        _run(*args)
    except Exception as err:   # noqa: BLE001 - no browser installed, or the server is not reachable
        logger.warning("guide screenshots skipped: %s", err)
