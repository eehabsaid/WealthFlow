"""Page-side JS that closes every open Bootstrap modal without tripping Bootstrap's state machine.

Why not `inst.hide(); inst.dispose();` back to back: hide() only QUEUES Bootstrap's _hideModal() (it runs after the
fade transition), and dispose() sets every instance property to null, so the queued callback later throws
"Cannot read properties of null (reading 'style')" (reproduced against the vendored Bootstrap 5.3.2). The shared
#globalModal instance must still be disposed after hiding (see static/js/app/modals.js closeModal), so we wait for the
`hidden.bs.modal` event and only then dispose. A modal still fading IN is first allowed to finish opening, because
Bootstrap ignores hide() while a transition runs. If the event never arrives (1.5 s) the instance is NOT disposed;
the forced class/style reset below still closes it visually and showModal() waits out a pending close itself.
"""

CLOSE_MODALS_JS = """async () => {
    const waitFor = (el, evt, ms) => new Promise((resolve) => {
        const timer = setTimeout(() => resolve(false), ms);
        el.addEventListener(evt, () => { clearTimeout(timer); resolve(true); }, { once: true });
    });
    if (typeof clearGoldPurityReturnContext === 'function') {
        clearGoldPurityReturnContext();
    }
    if (typeof goldPurityReturnContext !== 'undefined') {
        goldPurityReturnContext = null;
    }
    const Modal = window.bootstrap && window.bootstrap.Modal;
    const openModals = document.querySelectorAll('.modal.show, .modal[style*="display: block"]');
    for (const m of openModals) {
        const inst = Modal ? Modal.getInstance(m) : null;
        if (inst) {
            try {
                if (inst._isTransitioning && inst._isShown) await waitFor(m, 'shown.bs.modal', 1500);
                let hidden = true;
                if (inst._isShown || inst._isTransitioning) {
                    const done = waitFor(m, 'hidden.bs.modal', 1500);
                    inst.hide();
                    hidden = await done;
                }
                if (hidden) inst.dispose();
            } catch (e) {}
        }
        m.classList.remove('show');
        m.style.display = 'none';
        m.setAttribute('aria-hidden', 'true');
    }
    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
    document.body.style.removeProperty('overflow');
}"""
