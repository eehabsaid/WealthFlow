"use strict";

function isPrivilegedUser() {
  const u = window._currentUser || {};
  return !!u.is_sysadmin;
}

// True when the user's trial/subscription has lapsed (sysadmins are never locked). The server enforces the same
// rule with 402 on the data API; this keeps the UI on the upgrade page instead of a half-broken app.
function isSubscriptionLapsed() {
  if (isPrivilegedUser()) {
    return false;
  }
  const sub = window._billingSubscription;
  return !!(sub && sub.has_access === false);
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
