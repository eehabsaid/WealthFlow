/* ════════════════════════════════════════════════════════════════════════════
   financial_advisor.js — Financial Advisor module skeleton (Phase AI-0)
   ════════════════════════════════════════════════════════════════════════════ */
"use strict";

const FINANCIAL_ADVISOR_TABS = [
  { id: "overview", key: "financial_advisor_tab_overview" },
  { id: "cash-flow-forecast", key: "financial_advisor_tab_cash_flow_forecast" },
  { id: "wealth-growth-forecast", key: "financial_advisor_tab_wealth_growth_forecast" },
  { id: "portfolio-optimizer", key: "financial_advisor_tab_portfolio_optimizer" },
  { id: "goal-planning", key: "financial_advisor_tab_goal_planning" },
  { id: "risk-analysis", key: "financial_advisor_tab_risk_analysis" },
  { id: "spending-intelligence", key: "financial_advisor_tab_spending_intelligence" },
  { id: "opportunity-detection", key: "financial_advisor_tab_opportunity_detection" },
  { id: "market-intelligence", key: "financial_advisor_tab_market_intelligence" },
  { id: "ai-financial-advisor", key: "financial_advisor_tab_ai_financial_advisor" },
  { id: "what-if-simulator", key: "financial_advisor_tab_what_if_simulator" },
];

const FINANCIAL_ADVISOR_ACTIVE_TAB_KEY = "wf_financial_advisor_active_tab";
let _cashFlowForecastLoaded = false;
let _cashFlowForecastData = null;

function _cashFlowPaneId() {
  return "fa-pane-cash-flow-forecast";
}

function _money(value) {
  return fmtpresent(value || 0);
}

function _eventTranslationKey(eventType) {
  return `cash_flow_event_${eventType || "none"}`;
}

function _renderCashFlowLoading() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="cash_flow_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderCashFlowError() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="cash_flow_error"></span>
    </div>
  `;
  applyTranslations();
}

function _renderCashFlowForecast(payload) {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  const cp = payload?.checkpoints || {};
  const timeline = payload?.timeline || [];
  const summary = payload?.summary || {};
  const warnings = payload?.warnings || [];

  const cards = [
    { key: "cash_flow_card_current", value: cp.current || 0 },
    { key: "cash_flow_card_30", value: cp.days_30 || 0 },
    { key: "cash_flow_card_90", value: cp.days_90 || 0 },
    { key: "cash_flow_card_180", value: cp.days_180 || 0 },
    { key: "cash_flow_card_365", value: cp.days_365 || 0 },
  ];

  const cardsHtml = cards.map((card) => `
    <div class="col-12 col-sm-6 col-xl">
      <div class="asset-summary-card h-100" style="background:var(--bg-secondary);">
        <div class="asset-summary-label" data-i18n="${card.key}"></div>
        <div class="asset-summary-value">${_money(card.value)}</div>
      </div>
    </div>
  `).join("");

  const warningHtml = warnings.map((warning) => `
    <div class="alert alert-${warning.level || "secondary"}" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary); margin-bottom:10px;">
      <span data-i18n="${warning.key}"></span>
    </div>
  `).join("");

  const langCode = currentLang ? currentLang() : (document.documentElement.lang || "en");
  const monthFmt = new Intl.DateTimeFormat(langCode, { month: "long", year: "numeric" });

  const timelineHtml = timeline.map((month) => {
    const monthDate = `${month.month || ""}-01`;
    const monthLabel = month.month ? monthFmt.format(new Date(monthDate)) : "";
    const eventsHtml = (month.events || []).map((event) => {
      const isPositive = Number(event.amount || 0) >= 0;
      const sign = isPositive ? "+" : "-";
      const amountText = _money(Math.abs(Number(event.amount || 0)));
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-color);">
          <span style="color:var(--text-primary);" data-i18n="${_eventTranslationKey(event.type)}"></span>
          <span style="color:var(--text-secondary); font-weight:600;">${sign}${amountText}</span>
        </div>
      `;
    }).join("");

    return `
      <div class="card border-0 mb-3" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
        <div class="card-body" style="padding:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="color:var(--text-primary); font-weight:700;">${monthLabel}</div>
            <div style="color:var(--text-secondary); font-size:12px;">
              <span data-i18n="cash_flow_month_end_cash"></span>: ${_money(month.ending_cash || 0)}
            </div>
          </div>
          ${eventsHtml || `<div style="color:var(--text-secondary);" data-i18n="cash_flow_no_events"></div>`}
        </div>
      </div>
    `;
  }).join("");

  const largestEvent = summary.largest_cash_event || {};
  const largestExpense = summary.largest_planned_expense || {};
  const nearestMaturity = summary.nearest_certificate_maturity || {};

  pane.innerHTML = `
    <div class="row g-3 mb-4">
      ${cardsHtml}
    </div>

    <div class="mb-4">
      ${warningHtml}
    </div>

    <div class="mb-4">
      <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_timeline_title"></div>
      ${timelineHtml}
    </div>

    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_summary_title"></div>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_increase"></div>
              <div class="asset-summary-value">${_money(summary.expected_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_decrease"></div>
              <div class="asset-summary-value">${_money(summary.expected_decrease || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_net_change"></div>
              <div class="asset-summary-value">${_money(summary.net_cash_change || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_cash_event"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestEvent.type)}"></div>
              <div class="asset-summary-value">${_money(Math.abs(largestEvent.amount || 0))}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_nearest_maturity"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;">${nearestMaturity.date || "-"}</div>
              <div class="asset-summary-value">${_money(nearestMaturity.amount || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_planned_expense"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestExpense.type)}"></div>
              <div class="asset-summary-value">${_money(largestExpense.amount || 0)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  applyTranslations();
}

async function loadCashFlowForecast(force = false) {
  if (_cashFlowForecastData && !force) {
    _renderCashFlowForecast(_cashFlowForecastData);
    _cashFlowForecastLoaded = true;
    return;
  }

  _renderCashFlowLoading();
  try {
    const response = await fetch("/api/financial-advisor/cash-flow-forecast/");
    if (!response.ok) {
      throw new Error("cash_flow_fetch_failed");
    }
    const payload = await response.json();
    _cashFlowForecastData = payload;
    _renderCashFlowForecast(payload);
    _cashFlowForecastLoaded = true;
  } catch (error) {
    _renderCashFlowError();
  }
}

function renderFinancialAdvisor() {
  const main = document.getElementById("main-content");
  if (!main) return;

  const savedTab = sessionStorage.getItem(FINANCIAL_ADVISOR_ACTIVE_TAB_KEY) || "overview";
  const hasSavedTab = FINANCIAL_ADVISOR_TABS.some((tab) => tab.id === savedTab);
  const activeTabId = hasSavedTab ? savedTab : "overview";

  const tabsNav = FINANCIAL_ADVISOR_TABS.map((tab, index) => `
    <button
      class="settings-tab ${tab.id === activeTabId ? "active" : ""}"
      id="fa-tab-${tab.id}"
      data-bs-toggle="pill"
      data-bs-target="#fa-pane-${tab.id}"
      type="button"
      role="tab"
      aria-controls="fa-pane-${tab.id}"
      aria-selected="${tab.id === activeTabId ? "true" : "false"}"
      data-i18n="${tab.key}"
    ></button>
  `).join("");

  const tabsContent = FINANCIAL_ADVISOR_TABS.map((tab, index) => `
    <div
      class="tab-pane fade ${tab.id === activeTabId ? "show active" : ""}"
      id="fa-pane-${tab.id}"
      role="tabpanel"
      aria-labelledby="fa-tab-${tab.id}"
      tabindex="0"
    >
      ${tab.id === "cash-flow-forecast" ? `
      <div id="fa-cash-flow-content"></div>
      ` : `
      <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
        <div class="card-body" style="padding:24px;">
          <h5 style="color:var(--text-primary); margin-bottom:10px;" data-i18n="financial_advisor_feature_coming_soon"></h5>
          <p style="color:var(--text-secondary); margin:0;" data-i18n="financial_advisor_next_phase_description"></p>
        </div>
      </div>
      `}
    </div>
  `).join("");

  main.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">
          <i class="bi bi-brilliance" style="color:var(--text-primary);"></i>
          <span data-i18n="nav_financial_advisor"></span>
        </div>
      </div>
    </div>

    <div class="card border-0" style="background:var(--bg-primary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap" id="financialAdvisorTabs" role="tablist">
          ${tabsNav}
        </div>
        <div class="tab-content" id="financialAdvisorTabsContent">
          ${tabsContent}
        </div>
      </div>
    </div>
  `;

  applyTranslations();

  const tabsContainer = document.getElementById("financialAdvisorTabs");
  if (tabsContainer) {
    tabsContainer.querySelectorAll('[data-bs-toggle="pill"]').forEach((tabButton) => {
      tabButton.addEventListener("shown.bs.tab", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const targetSelector = target.getAttribute("data-bs-target") || "";
        const tabId = target.id.replace("fa-tab-", "");
        if (tabId) {
          sessionStorage.setItem(FINANCIAL_ADVISOR_ACTIVE_TAB_KEY, tabId);
        }
        if (targetSelector === `#${_cashFlowPaneId()}`) {
          loadCashFlowForecast();
        }
      });
    });
  }

  if (activeTabId === "cash-flow-forecast") {
    loadCashFlowForecast();
  }
}

window.renderFinancialAdvisor = renderFinancialAdvisor;
