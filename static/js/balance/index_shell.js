"use strict";

// balance/index_shell.js — Phase 10-14 of renderBalance: resolve active tab,
// build tab nav/pane markup, inject page shell, and dispatch tab renders.
// Split out of index.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceShell(mc, tabData) {
  // ── Resolve active tab ────────────────────────────────────────────────────
  const saved = sessionStorage.getItem(BALANCE_ACTIVE_TAB_KEY) || "overview";
  const activeTabId = BALANCE_TABS.some((tab) => tab.id === saved) ? saved : "overview";

  // ── Build tab nav buttons ──────────────────────────────────────────────────
  const tabsNav = BALANCE_TABS.map(
    (tab) => `
        <button
          class="wf-tab ${tab.id === activeTabId ? "active" : ""}"
          id="bal-tab-${tab.id}"
          data-bs-toggle="pill"
          data-bs-target="#bal-pane-${tab.id}"
          type="button"
          role="tab"
          aria-controls="bal-pane-${tab.id}"
          aria-selected="${tab.id === activeTabId ? "true" : "false"}"
          data-i18n="${tab.key}"
        ></button>`
  ).join("");

  // ── Build tab pane shells ───────────────────────────────────────────────────
  const tabPanes = BALANCE_TABS.map(
    (tab) => `
        <div class="tab-pane fade ${tab.id === activeTabId ? "show active" : ""}"
             id="bal-pane-${tab.id}"
             role="tabpanel"
             aria-labelledby="bal-tab-${tab.id}"
             tabindex="0">
        </div>`
  ).join("");

  const activeTabObj = BALANCE_TABS.find((t) => t.id === activeTabId) || BALANCE_TABS[0];
  const activeKey = activeTabObj.key;

  // ── Inject page shell ────────────────────────────────────────────────────
  mc.innerHTML = `
        <div class="page-header balance-page-header">
            <div><div class="page-title" data-i18n="${activeKey}">${t(activeKey)}</div></div>
        </div>
        <div class="card border-0 balance-page-card" style="background:var(--bg-primary);border:1px solid var(--border-color);">
            <div class="card-body" style="padding:16px;">
                <div class="wf-tabs-shell">
                    <div class="wf-tabs-row" id="balanceTabs" role="tablist">
                        ${tabsNav}
                    </div>
                </div>
                <div class="tab-content" id="balanceTabsContent" style="padding-top:16px;">
                    ${tabPanes}
                </div>
            </div>
        </div>
    `;

  applyTranslations();

  if (typeof window.initTabsWithMoreMenu === "function") {
    window.initTabsWithMoreMenu({
      containerId: "balanceTabs",
      visibleCount: 4,
      moreLabel: typeof t === "function" ? t("financial_advisor_tab_more", "More") : "More",
    });
  }

  // ── Render all tab panes immediately (all data is already in memory) ─────
  renderBalanceOverview(tabData);
  renderBalanceAllocation(tabData);
  renderBalanceForecasts(tabData);
  renderBalanceRecommendations(tabData);
  renderBalanceAccounts(tabData);
  if (typeof renderBalanceTransfers === "function") {
    renderBalanceTransfers(tabData);
  }
  if (typeof renderBalanceCurrencyExchange === "function") {
    renderBalanceCurrencyExchange(tabData);
  }
  if (typeof renderBalanceBankInterest === "function") {
    renderBalanceBankInterest(tabData);
  }
  if (typeof renderBalanceCreditCardPayment === "function") {
    renderBalanceCreditCardPayment(tabData);
  }
  if (typeof renderBalanceCardRenewalFee === "function") {
    renderBalanceCardRenewalFee(tabData);
  }

  applyTranslations();

  return activeTabId;
}
