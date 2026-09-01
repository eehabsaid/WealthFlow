// app.js — Application bootstrap, routing, sidebar, modals, toasts, utilities

"use strict";

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

let _companies = [];
let _banks = [];
let _activeRoute = "";
let _allowedPages = [];
let _appInitialized = false;
const SIDEBAR_MODE_KEY = "wf_sidebar_mode";
const SIDEBAR_MODES = ["expanded", "collapsed", "hidden"];
let _sidebarDesktopMode = localStorage.getItem(SIDEBAR_MODE_KEY) || "expanded";

window.translations = {};

// ════════════════════════════════════════════════════════════════════════════
// BOOTSTRAP
// ════════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  applyStoredTheme();
  await loadLanguage(localStorage.getItem("lang") || "en");
  await initApp();
  _appInitialized = true;
  window.__wfRouterReady = true;
  window.addEventListener("hashchange", route);
  route();
});

document.addEventListener("languageChanged", () => {
  if (_appInitialized && typeof route === "function") {
    route();
  }
});

async function initApp() {
  const [cRes, bRes, meRes, profileRes] = await Promise.all([
    fetch("/api/companies/"),
    fetch("/api/banks/"),
    fetch("/api/auth/me/"),
    fetch("/api/auth/profile/"),
  ]);

  const [cData, bData, meData, pData] = await Promise.all([
    cRes.json(),
    bRes.json(),
    meRes.json(),
    profileRes.json(),
  ]);

  _companies = cData.companies || [];
  _banks = bData.banks || [];
  _allowedPages = meData.allowed_pages || [];

  // Merge user info from both endpoints
  window._currentUser = { ...meData.user, ...pData.profile };

  renderSidebar();
  renderTopbar();
  applySidebarDesktopMode(_sidebarDesktopMode, true);

  // Check reminders in background after load
  setTimeout(() => {
    if (typeof checkReminders === "function") checkReminders();
  }, 2000);
}

// GLOBAL EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.navigate = navigate;
window.showModal = showModal;
window.closeModal = closeModal;
window.showToast = showToast;
window.fmt = fmt;
window.fmtpresent = fmtpresent;
window.fmtInt = fmtInt;
window.amtClass = amtClass;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.loadingHTML = loadingHTML;
window.setBreadcrumb = setBreadcrumb;
window.renderSidebar = renderSidebar;
window.loadLangMenu = loadLangMenu;
window.toggleMobileSidebar = toggleMobileSidebar;
window.closeMobileSidebar = closeMobileSidebar;
window.toggleSidebarDesktopMode = toggleSidebarDesktopMode;
window.doLogout = doLogout;
window.showProfileModal = showProfileModal;
window.previewAndUploadAvatar = previewAndUploadAvatar;
window.saveProfile = saveProfile;
window.toggleTheme = toggleTheme;
window.applyStoredTheme = applyStoredTheme;
window.initTabsWithMoreMenu = initTabsWithMoreMenu;
window.renderTabsShell = renderTabsShell;
window.renderFixedAssets = window.renderFixedAssets;
window.refreshCompanies = async () => {
  const r = await fetch("/api/companies/");
  _companies = (await r.json()).companies || [];
};
