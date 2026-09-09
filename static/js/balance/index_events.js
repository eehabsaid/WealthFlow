"use strict";

// balance/index_events.js — Phase 15 of renderBalance: wire tab switch events
// (session storage persistence & Add button visibility). Split out of
// index.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function wireBalanceTabEvents(activeTabId) {
  if (_balanceTabEventsAbortController) {
    _balanceTabEventsAbortController.abort();
  }
  _balanceTabEventsAbortController = new AbortController();
  const signal = _balanceTabEventsAbortController.signal;

  const updateAddBtn = (tabId) => {
    const btn = document.getElementById("addEntryBtn");
    if (btn) btn.style.display = tabId === "accounts" ? "inline-block" : "none";
  };
  updateAddBtn(activeTabId);

  const tabsContainer = document.getElementById("balanceTabs");
  if (tabsContainer) {
    tabsContainer.querySelectorAll('[data-bs-toggle="pill"]').forEach((btn) => {
      btn.addEventListener(
        "shown.bs.tab",
        (e) => {
          const target = e.target;
          if (!(target instanceof HTMLElement)) return;
          const tabId = target.id.replace("bal-tab-", "");
          if (tabId) {
            sessionStorage.setItem(BALANCE_ACTIVE_TAB_KEY, tabId);
            updateAddBtn(tabId);
            const activeTabObj = BALANCE_TABS.find((t) => t.id === tabId) || BALANCE_TABS[0];
            const activeKey = activeTabObj.key;
            const titleEl = document.querySelector(".balance-page-header .page-title");
            if (titleEl) {
              titleEl.setAttribute("data-i18n", activeKey);
              titleEl.textContent = t(activeKey);
            }
          }
        },
        { signal }
      );
    });
  }
}
