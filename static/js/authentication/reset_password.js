'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.querySelector('input[name="password"]');
    const confirmInput = document.querySelector('input[name="confirm_password"]');
    const matchWarning = document.getElementById('resetMatchWarning');

    if (window.WFAuth && window.WFAuth.setupCapsLockListener) {
        window.WFAuth.setupCapsLockListener('resetPasswordInput', 'resetCapsLockWarning');
    }

    function checkMatch() {
        if (!passwordInput || !confirmInput || !matchWarning) return;
        if (confirmInput.value && passwordInput.value !== confirmInput.value) {
            matchWarning.style.display = 'block';
            confirmInput.classList.add('is-invalid-custom');
            confirmInput.classList.remove('is-valid-custom');
        } else if (confirmInput.value && passwordInput.value === confirmInput.value) {
            matchWarning.style.display = 'none';
            confirmInput.classList.remove('is-invalid-custom');
            confirmInput.classList.add('is-valid-custom');
        } else {
            matchWarning.style.display = 'none';
            confirmInput.classList.remove('is-invalid-custom', 'is-valid-custom');
        }
    }

    if (passwordInput && confirmInput) {
        passwordInput.addEventListener('input', checkMatch);
        confirmInput.addEventListener('input', checkMatch);
    }
});
