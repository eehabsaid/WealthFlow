"use strict";
// Sidebar settings nav section: divider + settings button.
// Split out of renderSidebar (200-line rule). Do not edit directly.

function buildSidebarSettingsNavHtml(showWelcomeOnly, canSettings) {
  return `${!showWelcomeOnly && canSettings ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

            ${
              !showWelcomeOnly && canSettings
                ? `
            <button class="nav-item" onclick="navigate('settings-languages')">
                <i class="bi bi-gear"></i>
                <span data-i18n="nav_settings">Settings</span>
            </button>`
                : ""
            }

`;
}
