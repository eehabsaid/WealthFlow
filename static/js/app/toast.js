'use strict';

function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    const id        = 'toast-' + Date.now();
    const color     = type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)';
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast align-items-center" role="alert"
             style="border-left:3px solid ${color}">
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast"></button>
            </div>
        </div>`);
    new bootstrap.Toast(document.getElementById(id), { delay: 3000 }).show();
}

// ════════════════════════════════════════════════════════════════════════════
// NUMBER FORMATTERS
// ════════════════════════════════════════════════════════════════════════════

