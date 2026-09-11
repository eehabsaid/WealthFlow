"use strict";
// ════════════════════════════════════════════════════════════════════════════
// TOPBAR
// ════════════════════════════════════════════════════════════════════════════

function applySidebarDesktopMode(mode, skipPersist = false) {
  const normalized = SIDEBAR_MODES.includes(mode) ? mode : "expanded";
  _sidebarDesktopMode = normalized;
  document.documentElement.setAttribute("data-sidebar-mode", normalized);
  if (!skipPersist) {
    localStorage.setItem(SIDEBAR_MODE_KEY, normalized);
  }
  updateSidebarModeButton();
}

function updateSidebarModeButton() {
  const btn = document.getElementById("desktop-sidebar-mode-btn");
  if (!btn) return;

  let icon = "bi-layout-sidebar-inset";
  let title = "Sidebar: Expanded";
  if (_sidebarDesktopMode === "collapsed") {
    icon = "bi-layout-sidebar";
    title = "Sidebar: Collapsed";
  } else if (_sidebarDesktopMode === "hidden") {
    icon = "bi-layout-sidebar-reverse";
    title = "Sidebar: Hidden";
  }

  btn.setAttribute("title", `${title} (click to change)`);
  btn.setAttribute("aria-label", title);
  btn.innerHTML = `<i class="bi ${icon}"></i>`;
}

function toggleSidebarDesktopMode() {
  const currentIndex = SIDEBAR_MODES.indexOf(_sidebarDesktopMode);
  const nextIndex = (currentIndex + 1) % SIDEBAR_MODES.length;
  applySidebarDesktopMode(SIDEBAR_MODES[nextIndex]);
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const open = sidebar.classList.toggle("open");
  overlay?.classList.toggle("show", open);
}

function closeMobileSidebar() {
  document.getElementById("sidebar")?.classList.remove("open");
  document.getElementById("sidebarOverlay")?.classList.remove("show");
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION TOGGLE (collapsible nav sections)
// ════════════════════════════════════════════════════════════════════════════
