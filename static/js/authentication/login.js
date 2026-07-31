'use strict';

document.addEventListener('DOMContentLoaded', () => {
    // Page-specific initialization for Login view (defers focus safely to prevent autofocus collision warnings)
    setTimeout(() => {
        const usernameInput = document.querySelector('input[name="username"]');
        if (usernameInput && document.activeElement !== usernameInput && !usernameInput.value) {
            usernameInput.focus();
        }
    }, 100);

    if (window.WFAuth && window.WFAuth.setupCapsLockListener) {
        window.WFAuth.setupCapsLockListener('passwordInput', 'capsLockWarning');
    }
});
