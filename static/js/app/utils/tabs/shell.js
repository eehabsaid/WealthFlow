"use strict";
// Tabs row shell HTML wrapper.
// Part of the app/utils module (split from the former monolithic tabs.js,
// 200-line rule). Do not edit directly.

function renderTabsShell(containerId, tabButtonsHtml) {
  return `
        <div class="wf-tabs-shell">
            <div class="wf-tabs-row" id="${containerId}" role="tablist">
                ${tabButtonsHtml}
            </div>
        </div>
    `;
}
