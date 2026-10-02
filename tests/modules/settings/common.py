"""Shared helper for tests/modules/settings/ phase files."""

import time


def _uid():
    return str(int(time.time() * 1000))[-6:]


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
