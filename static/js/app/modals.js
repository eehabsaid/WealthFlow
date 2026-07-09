'use strict';

function showModal(html) {
    let el = document.getElementById('globalModal');
    if (!el) {
        el = document.createElement('div');
        el.id        = 'globalModal';
        el.className = 'modal fade modal-dark';
        el.setAttribute('tabindex', '-1');
        document.body.appendChild(el);
    }

    //<div class="modal-dialog modal-dialog-centered"> small dialog
    el.innerHTML = `
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">${html}</div>
        </div>`;
    bootstrap.Modal.getInstance(el)?.dispose();
    const modal = new bootstrap.Modal(el, {
        backdrop: 'static',
        keyboard: false,
    });
    modal.show();
}

function closeModal() {
    const el = document.getElementById('globalModal');
    if (el) bootstrap.Modal.getInstance(el)?.hide();
}

// ════════════════════════════════════════════════════════════════════════════
// TOAST
// ════════════════════════════════════════════════════════════════════════════

