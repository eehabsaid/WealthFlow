"""Helpers for the AI workspace sidebar, which is an off-canvas drawer on phones (width <= 767.98px)."""


def open_ai_drawer(page):
    """Open the drawer when it is closed and the toggle is shown (phones); no-op on desktop/tablet."""
    toggle = page.query_selector(".ai-ws-sidebar-toggle")
    if toggle and toggle.is_visible() and not page.query_selector(".ai-ws-left--open"):
        toggle.click()
        page.wait_for_selector(".ai-ws-left--open", timeout=3000)
        page.wait_for_timeout(350)  # slide-in transition


def close_ai_drawer(page):
    """Close the drawer again so later steps are not covered by its overlay."""
    if page.query_selector(".ai-ws-left--open"):
        page.evaluate("() => _toggleAISidebar()")
        page.wait_for_timeout(300)
