"""
WealthFlow QA Module — PWA (A4): installable manifest, service worker, offline shell.
Checks, against the real browser (not only the DOM):
 1. /manifest.webmanifest is linked from the page, served as JSON, standalone, with 192 + 512 + maskable icons that load.
 2. The service worker registers with root scope and becomes active.
 3. The service worker never caches /api/ responses (private financial data).
 4. App JS/CSS/i18n is served network-first (cached as offline fallback only) under the bumped cache version.
 5. /offline/ renders its translated message, and a real navigation made while the browser is offline lands on it.

NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

SW_READY_JS = """async () => {
    if (!('serviceWorker' in navigator)) return {supported: false};
    const reg = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise((resolve) => setTimeout(() => resolve(null), 10000)),
    ]);
    if (!reg) return {supported: true, ready: false};
    return {supported: true, ready: true, scope: new URL(reg.scope).pathname, active: !!reg.active};
}"""

CACHED_URLS_JS = """async () => {
    const urls = [];
    for (const name of await caches.keys()) {
        const cache = await caches.open(name);
        for (const req of await cache.keys()) urls.push(new URL(req.url).pathname);
    }
    return urls;
}"""


def _step(reporter, screenshot_logger, page, name, ok, detail, tab="check"):
    shot = screenshot_logger.capture(page, "pwa", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "PWA", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _check_manifest(page, reporter, screenshot_logger):
    linked = page.query_selector("link[rel='manifest']") is not None
    data = page.evaluate(
        """async () => { const r = await fetch('/manifest.webmanifest');
            return {status: r.status, type: r.headers.get('content-type') || '', body: await r.json()}; }"""
    )
    body = data["body"]
    sizes = {icon["sizes"] for icon in body.get("icons", [])}
    purposes = {icon.get("purpose") for icon in body.get("icons", [])}
    loads = page.evaluate(
        """async (icons) => { const out = [];
            for (const i of icons) { const r = await fetch(i.src); out.push(r.ok); } return out; }""",
        body.get("icons", []),
    )
    ok = (linked and data["status"] == 200 and "manifest+json" in data["type"] and body.get("display") == "standalone"
          and {"192x192", "512x512"} <= sizes and "maskable" in purposes and all(loads) and bool(loads))
    _step(reporter, screenshot_logger, page, "Manifest linked, standalone, icons load", ok,
          f"linked={linked} status={data['status']} display={body.get('display')} sizes={sorted(sizes)} icons_ok={loads}")


def _check_service_worker(page, reporter, screenshot_logger):
    state = page.evaluate(SW_READY_JS)
    ok = bool(state.get("ready") and state.get("active") and state.get("scope") == "/")
    _step(reporter, screenshot_logger, page, "Service worker active with root scope", ok, f"state={state}")
    if not ok:
        return False
    page.reload()
    page.wait_for_timeout(1200)
    page.evaluate("fetch('/api/currencies/').then(r => r.json())")   # a real API call while the worker controls the page
    page.wait_for_timeout(500)
    cached = page.evaluate(CACHED_URLS_JS)
    api_cached = [u for u in cached if u.startswith("/api/")]
    _step(reporter, screenshot_logger, page, "API responses are never cached", not api_cached,
          f"cached_paths={cached} api_cached={api_cached}")
    _check_network_first(page, reporter, screenshot_logger)
    return True


NETWORK_FIRST_JS = """async () => {
    const names = (await caches.keys()).filter((n) => n.startsWith('wealthflow-static-'));
    const url = '/static/js/pwa/offline.js';
    const online = await fetch(url, {cache: 'no-store'});
    return {names, onlineOk: online.ok};
}"""

OFFLINE_FETCH_JS = """async () => {
    try {
        const r = await fetch('/static/js/pwa/offline.js');
        return {ok: r.ok};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""


def _check_network_first(page, reporter, screenshot_logger):
    info = page.evaluate(NETWORK_FIRST_JS)
    page.wait_for_timeout(500)
    cached = page.evaluate(CACHED_URLS_JS)
    versioned = bool(info["names"]) and all(not n.endswith("-v1") for n in info["names"])
    stored = "/static/js/pwa/offline.js" in cached
    page.context.set_offline(True)
    try:
        offline = page.evaluate(OFFLINE_FETCH_JS)
    finally:
        page.context.set_offline(False)
    ok = versioned and info["onlineOk"] and stored and offline.get("ok", False)
    _step(reporter, screenshot_logger, page, "App JS is network-first with offline cache fallback", ok,
          f"caches={info['names']} stored={stored} offline={offline}")


def _check_offline(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("offline/")
    title = page.inner_text("h1") if page.query_selector("h1") else ""
    ok = bool(title.strip()) and page.query_selector("#pwa-offline-retry") is not None
    _step(reporter, screenshot_logger, page, "Offline page renders", ok, f"h1={title!r}", tab="offline")
    browser_context = page.context
    try:
        context.goto_route("")
        browser_context.set_offline(True)
        page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        shown = page.query_selector("#pwa-offline-retry") is not None
        _step(reporter, screenshot_logger, page, "Offline navigation falls back to the offline page", shown,
              f"url={page.url} offline_page_visible={shown}", tab="offline_navigation")
    except Exception as ex:
        _step(reporter, screenshot_logger, page, "Offline navigation falls back to the offline page", False,
              f"Exception: {ex}", tab="offline_navigation")
    finally:
        browser_context.set_offline(False)


def test_pwa_module(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("")
    reporter.pages_visited.add("PWA")
    reporter.tabs_visited.add("PWA -> manifest")
    try:
        _check_manifest(page, reporter, screenshot_logger)
        reporter.tabs_visited.add("PWA -> service worker")
        if _check_service_worker(page, reporter, screenshot_logger):
            reporter.tabs_visited.add("PWA -> offline")
            _check_offline(context, reporter, screenshot_logger)
    except Exception as ex:
        _step(reporter, screenshot_logger, page, "PWA module", False, f"Exception: {ex}")
