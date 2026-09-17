"use strict";

function isPrivilegedUser() {
  const u = window._currentUser || {};
  return !!u.is_sysadmin;
}

function hasPermission(key) {
  if (isPrivilegedUser()) {
    return true;
  }
  return (_allowedPages || []).includes(key);
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

function planAllowsAIWorkspace() {
  if (isPrivilegedUser()) {
    return true;
  }
  const sub = window._billingSubscription;
  return !!(sub && sub.plan && sub.plan.allows_ai_workspace);
}
