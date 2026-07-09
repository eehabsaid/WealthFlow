'use strict';

function isPrivilegedUser() {
    const u = window._currentUser || {};
    return !!(u.is_staff || u.is_superuser);
}

function canAccessAny(requiredKeys) {
    if (isPrivilegedUser()) {
        return true;
    }
    const allowed = new Set(_allowedPages || []);
    return requiredKeys.some((key) => allowed.has(key));
}

function hasAnyAssignedPageAccess() {
    if (isPrivilegedUser()) {
        return true;
    }
    return (_allowedPages || []).length > 0;
}

function shouldShowWelcomeOnly() {
    return !hasAnyAssignedPageAccess();
}

