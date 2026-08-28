"""
AI Tool Handlers — Live App Structure discovery group.

NOTE (200-line file convention): part of the core/services/ai/tools/
package (see tools/__init__.py for the full convention). If this file
grows past 200 lines, split it further into more files within this same
package.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Tool Handlers ─────────────────────────────────────────────────────────────

def _get_live_django_routes() -> list[dict[str, str]]:
    """Walks Django's URL resolver recursively to return real registered named routes."""
    from django.urls import get_resolver, URLPattern, URLResolver

    routes = []
    seen = set()

    def _recurse(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLResolver):
                _recurse(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                path_str = "/" + (prefix + str(p.pattern)).lstrip("^/").rstrip("$")
                clean_path = "/" + path_str.strip("/")
                if clean_path == "/":
                    clean_path = "/"
                if any(clean_path.startswith(x) for x in ("/api/", "/static/", "/media/", "/admin/")):
                    continue
                if clean_path not in seen:
                    seen.add(clean_path)
                    routes.append({
                        "route": clean_path,
                        "name": p.name or "",
                    })

    _recurse(get_resolver().url_patterns)
    return routes


def _crawl_live_pages_with_playwright(
    base_url: str | list[dict[str, Any]] = "http://127.0.0.1:8001",
    routes_info: list[dict[str, Any]] | None = None,
    max_pages: int = 15,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Crawls live application pages in headless mode using Playwright to inspect rendered DOM.
    Returns (page_structures, crawl_error).
    CRITICAL CONSTRAINT: 100% READ-ONLY safe browsing - inspects DOM elements only, never submits forms or clicks write/delete actions.
    """
    if isinstance(base_url, list):
        base_url = "http://127.0.0.1:8001"

    structures = []
    crawl_error = None

    try:
        from playwright.sync_api import sync_playwright
        from tests.core.cdn_fallback import install_cdn_fallback

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            install_cdn_fallback(page)

            # Perform login as eehab_said / Eehabdev1
            login_url = f"{base_url.rstrip('/')}/accounts/login/"
            try:
                page.goto(login_url, timeout=8000)
                page.wait_for_load_state("networkidle", timeout=5000)

                if page.query_selector('input[name="username"]'):
                    page.fill('input[name="username"]', "eehab_said")
                    page.fill('input[name="password"]', "Eehabdev1")
                    page.click('button[type="submit"], input[type="submit"], .btn-login')
                    page.wait_for_load_state("networkidle", timeout=5000)
            except Exception as login_exc:
                logger.warning("Playwright login attempt error on %s: %s", login_url, login_exc)

            sections = [
                ("dashboard", "Dashboard"),
                ("financial-advisor", "Financial Advisor"),
                ("employment", "Employment"),
                ("balance", "Balance"),
                ("bank-certificates", "Bank Certificates"),
                ("fixed-assets", "Fixed Assets"),
                ("exchange-rates", "Exchange Rates"),
                ("gold-price", "Gold Price"),
                ("expenses", "Expenses"),
                ("expense-categories", "Categories"),
                ("reports", "Reports"),
                ("advanced-reports", "Advanced Reports"),
                ("settings", "Settings"),
            ]

            crawled_count = 0
            for route_name, fallback_title in sections:
                if crawled_count >= max_pages:
                    break
                crawled_count += 1
                url = f"{base_url.rstrip('/')}/#{route_name}" if route_name != "dashboard" else f"{base_url.rstrip('/')}/"
                try:
                    page.goto(url, timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=3000)
                    page.wait_for_timeout(200)

                    dom_data = page.evaluate("""() => {
                        const titleEl = document.querySelector('h1, h2, h3, .page-header, .brand-text, .page-title');
                        const pageTitle = titleEl ? titleEl.textContent.trim() : '';

                        const tabEls = Array.from(document.querySelectorAll(
                            '#main-content button, #main-content .nav-link, #main-content .nav-item, #main-content [role="tab"], #main-content .wf-tab, .nav-tabs .nav-link'
                        ));
                        const tabs = [];
                        const seenTabs = new Set();
                        tabEls.forEach(el => {
                            if (el.offsetParent === null || el.closest('.d-none')) return;
                            const text = el.textContent.trim();
                            if (text && text.length < 50 && !seenTabs.has(text.toLowerCase())) {
                                seenTabs.add(text.toLowerCase());
                                tabs.push({ name: text, id: el.id || '' });
                            }
                        });

                        const modalEls = Array.from(document.querySelectorAll(
                            '[data-bs-toggle="modal"], [onclick*="Modal"], [onclick*="show"], .modal-title'
                        ));
                        const modals = [];
                        const seenModals = new Set();
                        modalEls.forEach(el => {
                            const text = (el.textContent || el.getAttribute('title') || el.getAttribute('data-bs-target') || '').trim();
                            if (text && text.length < 50 && !seenModals.has(text.toLowerCase())) {
                                seenModals.add(text.toLowerCase());
                                modals.push(text);
                            }
                        });

                        return { pageTitle, tabs, modals };
                    }""")

                    structures.append({
                        "route": route_name,
                        "title": dom_data.get("pageTitle") or fallback_title,
                        "url": url,
                        "tabs": dom_data.get("tabs", []),
                        "modals_or_forms": dom_data.get("modals", []),
                        "status": "ok",
                    })
                except Exception as page_exc:
                    logger.warning("Skipped live crawl for route '%s': %s", route_name, page_exc)
                    structures.append({
                        "route": route_name,
                        "title": fallback_title,
                        "url": url,
                        "tabs": [],
                        "modals_or_forms": [],
                        "status": "error",
                        "error_reason": str(page_exc),
                    })

            browser.close()
    except Exception as exc:
        logger.error("Playwright browser execution failed: %s", exc, exc_info=True)
        crawl_error = str(exc)

    return structures, crawl_error
