"""Shared helper for tests/modules/settings/ phase files."""

import time


def _uid():
    return str(int(time.time() * 1000))[-6:]


# Real Settings tab routes (static/js/settings/tabs.js). There is NO global switchSettingsTab(); the tabs are
# plain routes, so a phase must navigate to "#settings-<tab>" or it stays on whatever tab was open before.
SETTINGS_TAB_ROUTES = {
    "languages": "settings-languages", "companies": "settings-companies", "banks": "settings-banks",
    "currencies": "settings-currency", "users": "settings-users", "roles": "settings-roles",
    "billing": "settings-billing", "email-templates": "settings-emailtemplates",
    "translations": "settings-translations", "translation-coverage": "settings-translationcoverage",
    "reminders": "settings-reminders", "cert-status": "settings-certstatus",
    "gold-settings": "settings-goldsettings", "property-valuation": "settings-propertyvaluation",
    "dashboard": "settings-dashboard", "backup": "settings-backuprestore",
    "documentation": "settings-documentation", "ai-advisor": "settings-aiadvisor", "my-ai": "settings-myai",
}


def open_settings_tab(context, tab, wait_ms=900):
    """Navigate to a Settings sub-tab and return True once that tab's route is active (hash matches)."""
    route = SETTINGS_TAB_ROUTES[tab]
    context.goto_route(f"#{route}")
    context.page.wait_for_timeout(wait_ms)
    return context.page.evaluate("location.hash") == f"#{route}"


_CLOSE_GLOBAL_MODAL_JS = """() => {
    const el = document.getElementById('globalModal');
    if (!el) return false;
    const wasOpen = el.classList.contains('show');
    const Modal = window.bootstrap && window.bootstrap.Modal;
    const inst = Modal ? Modal.getInstance(el) : null;
    // Project rule: after hide() always dispose() the shared #globalModal instance, or the next show() fails silently.
    if (inst) { try { inst.hide(); inst.dispose(); } catch (e) {} }
    el.classList.remove('show');
    el.style.display = 'none';
    el.setAttribute('aria-hidden', 'true');
    el.removeAttribute('aria-modal');
    document.querySelectorAll('.modal-backdrop').forEach((b) => b.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
    return wasOpen;
}"""


def close_global_modal(page):
    """Dismiss the shared #globalModal if a previous phase left it open (e.g. the Documentation Engine's
    "Generation Validation Failed" dialog, which stays up on a fresh run with no screenshots yet) so it cannot
    intercept clicks in the next phase. Returns True when a modal was open."""
    was_open = bool(page.evaluate(_CLOSE_GLOBAL_MODAL_JS))
    try:
        page.wait_for_function("() => !document.querySelector('#globalModal.show')", timeout=3000)
    except Exception:
        pass
    return was_open
