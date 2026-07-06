/* ════════════════════════════════════════════════════════════════════════════
   financial_advisor.js — Financial Advisor module skeleton (Phase AI-0)
   ════════════════════════════════════════════════════════════════════════════ */
"use strict";

const FINANCIAL_ADVISOR_TABS = [
  { id: "overview", key: "financial_advisor_tab_overview", shortKey: "financial_advisor_tab_overview" },
  { id: "cash-flow-forecast", key: "financial_advisor_tab_cash_flow_forecast", shortKey: "financial_advisor_tab_cash_flow" },
  { id: "wealth-growth-forecast", key: "financial_advisor_tab_wealth_growth_forecast", shortKey: "financial_advisor_tab_wealth_growth" },
  { id: "portfolio-optimizer", key: "financial_advisor_tab_portfolio_optimizer", shortKey: "financial_advisor_tab_portfolio" },
  { id: "goal-planning", key: "financial_advisor_tab_goal_planning" },
  { id: "risk-analysis", key: "financial_advisor_tab_risk_analysis" },
  { id: "spending-intelligence", key: "financial_advisor_tab_spending_intelligence" },
  { id: "opportunity-detection", key: "financial_advisor_tab_opportunity_detection", shortKey: "financial_advisor_tab_opportunities" },
  { id: "market-intelligence", key: "financial_advisor_tab_market_intelligence", shortKey: "financial_advisor_tab_performance" },
  { id: "ai-financial-advisor", key: "financial_advisor_tab_ai_financial_advisor" },
  { id: "what-if-simulator", key: "financial_advisor_tab_what_if_simulator" },
];

const FINANCIAL_ADVISOR_ACTIVE_TAB_KEY = "wf_financial_advisor_active_tab";
const FINANCIAL_ADVISOR_PRIMARY_TAB_IDS = [
  "overview",
  "cash-flow-forecast",
  "wealth-growth-forecast",
  "portfolio-optimizer",
];

let _cashFlowForecastLoaded = false;
let _cashFlowForecastData = null;
let _wealthGrowthForecastLoaded = false;
let _wealthGrowthForecastData = null;
let _wealthGrowthForecastThemeListenerAttached = false;
let _financialAdvisorMenuEventsAbortController = null;

function _cashFlowPaneId() {
  return "fa-pane-cash-flow-forecast";
}

function _money(value) {
  return fmtpresent(value || 0);
}

function _eventTranslationKey(eventType) {
  return `cash_flow_event_${eventType || "none"}`;
}

function _wealthComponentTitle(key) {
  return {
    none: "wealth_growth_component_none",
    liquid_cash: "wealth_growth_component_liquid_cash",
    fixed_assets: "wealth_growth_component_fixed_assets",
    gold: "wealth_growth_component_gold",
    certificates: "wealth_growth_component_certificates",
  }[key] || key;
}

function _scenarioTitle(key) {
  return {
    conservative: "wealth_growth_scenario_conservative",
    expected: "wealth_growth_scenario_expected",
    optimistic: "wealth_growth_scenario_optimistic",
  }[key] || key;
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

function _renderWealthGrowthLoading() {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="wealth_growth_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderWealthGrowthError() {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="wealth_growth_error"></span>
    </div>
  `;
  applyTranslations();
}

function _destroyChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !window.Chart) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
}

function _themeColor(variableName, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
  return value || fallback;
}

function _pageDirection() {
  const htmlDir = (document.documentElement.getAttribute("dir") || "ltr").toLowerCase();
  return htmlDir === "rtl" ? "rtl" : "ltr";
}

function _drawWealthGrowthChart(data) {
  const canvas = document.getElementById("wealthGrowthChart");
  if (!canvas || !window.Chart) return;

  _destroyChart("wealthGrowthChart");

  const direction = _pageDirection();
  const isRTL = direction === "rtl";
  const primaryText = _themeColor("--text-primary", "#e8f0fe");
  const secondaryText = _themeColor("--text-secondary", "#7b93c9");
  const gridColor = "rgba(123, 147, 201, 0.16)";

  canvas.setAttribute("dir", direction);
  canvas.style.direction = direction;
  const chartWrapper = canvas.parentElement;
  if (chartWrapper) {
    chartWrapper.setAttribute("dir", direction);
  }

  const labels = data.month_labels || [];
  const series = data.series || {};
  const conservative = (series.conservative?.points || []).map((p) => p.net_worth);
  const expected = (series.expected?.points || []).map((p) => p.net_worth);
  const optimistic = (series.optimistic?.points || []).map((p) => p.net_worth);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: t("wealth_growth_scenario_conservative", "Conservative"), data: conservative, borderColor: "#6c757d", backgroundColor: "rgba(108,117,125,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
        { label: t("wealth_growth_scenario_expected", "Expected"), data: expected, borderColor: "#1a6ef5", backgroundColor: "rgba(26,110,245,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
        { label: t("wealth_growth_scenario_optimistic", "Optimistic"), data: optimistic, borderColor: "#20c997", backgroundColor: "rgba(32,201,151,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { rtl: isRTL, reverse: isRTL, labels: { color: primaryText, textDirection: direction } },
        tooltip: {
          rtl: isRTL,
          textDirection: direction,
          titleColor: primaryText,
          bodyColor: primaryText,
          backgroundColor: "rgba(13, 21, 48, 0.96)",
          borderColor: gridColor,
          borderWidth: 1,
          callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.raw)}` },
        },
      },
      scales: {
        x: { reverse: isRTL, ticks: { color: secondaryText, textDirection: direction }, grid: { color: gridColor } },
        y: { position: isRTL ? "right" : "left", ticks: { color: secondaryText, align: isRTL ? "end" : "start" }, grid: { color: gridColor } },
      },
    },
  });
}

function _attachWealthGrowthThemeListener() {
  if (_wealthGrowthForecastThemeListenerAttached) return;
  window.addEventListener("themeChanged", () => {
    if (_wealthGrowthForecastLoaded && _wealthGrowthForecastData) {
      _renderWealthGrowthForecast(_wealthGrowthForecastData);
    }
  });
  _wealthGrowthForecastThemeListenerAttached = true;
}

function _renderWealthGrowthForecast(payload) {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  const current = payload?.current_net_worth || 0;
  const checkpoints = payload?.checkpoints || {};
  const breakdown = payload?.breakdown || {};
  const summary = payload?.summary || {};
  const scenarioCards = payload?.scenario_cards || {};

  const periodCards = [
    { key: "wealth_growth_current_net_worth", value: checkpoints.current || 0 },
    { key: "wealth_growth_end_next_month", value: checkpoints.next_month || 0 },
    { key: "wealth_growth_end_third_month", value: checkpoints.month_3 || 0 },
    { key: "wealth_growth_end_sixth_month", value: checkpoints.month_6 || 0 },
    { key: "wealth_growth_end_twelfth_month", value: checkpoints.month_12 || 0 },
  ];

  const scenarioCardKeys = ["conservative", "expected", "optimistic"];

  const scenarioCardsHtml = scenarioCardKeys.map((key) => {
    const card = scenarioCards[key] || {};
    return `
      <div class="col-12 col-md-4">
        <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.25); box-shadow:0 0 0 1px rgba(255,255,255,0.02) inset;">
          <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="${_scenarioTitle(key)}"></div>
          <div style="color:var(--text-primary); font-size:12px; margin-bottom:8px; opacity:0.9;" data-i18n="wealth_growth_scenario_label"></div>
          <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(card.forecast || 0)}</div>
          <div style="margin-top:8px; color:var(--text-primary); font-size:12px;">
            <span data-i18n="wealth_growth_difference"></span>: ${_money(card.difference || 0)}
          </div>
          <div style="color:var(--text-primary); font-size:12px;">
            <span data-i18n="wealth_growth_growth_pct"></span>: ${fmtpresent(card.growth_pct || 0)}%
          </div>
        </div>
      </div>
    `;
  }).join("");

  const breakdownKeys = ["liquid_cash", "fixed_assets", "gold", "certificates"];
  const breakdownHtml = breakdownKeys.map((key) => {
    const item = breakdown[key] || {};
    return `
      <div class="col-12 col-md-6 col-xl-3">
        <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18); box-shadow:0 0 0 1px rgba(255,255,255,0.02) inset;">
          <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="${_wealthComponentTitle(key)}"></div>
          <div style="display:grid;gap:6px;">
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_current"></span>: ${_money(item.current || 0)}</div>
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_forecast"></span>: ${_money(item.forecast || 0)}</div>
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_difference"></span>: ${_money(item.difference || 0)}</div>
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_growth_pct"></span>: ${fmtpresent(item.growth_pct || 0)}%</div>
          </div>
        </div>
      </div>
    `;
  }).join("");

  const insightKey = summary.insight_key || "wealth_growth_insight_balanced";

  pane.innerHTML = `
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px; height:360px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="wealth_growth_chart_title"></div>
        <div style="height:300px; position:relative;">
          <canvas id="wealthGrowthChart"></canvas>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      ${periodCards.map((card) => `
        <div class="col-12 col-sm-6 col-xl">
          <div class="asset-summary-card h-100" style="background:var(--bg-secondary);">
            <div class="asset-summary-label" data-i18n="${card.key}"></div>
            <div class="asset-summary-value">${_money(card.value)}</div>
          </div>
        </div>
      `).join("")}
    </div>

    <div class="row g-3 mb-4">
      ${scenarioCardsHtml}
    </div>

    <div class="row g-3 mb-4">
      ${breakdownHtml}
    </div>

    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="wealth_growth_summary_title"></div>
        <div class="row g-3">
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_expected_increase"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(summary.expected_net_worth_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_expected_growth_pct"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${fmtpresent(summary.expected_growth_pct || 0)}%</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_monthly_increase"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(summary.estimated_monthly_wealth_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_largest_appreciating_asset"></div>
              <div class="asset-summary-value" style="font-size:1.35rem; color:var(--text-primary);" data-i18n="${_wealthComponentTitle(summary.largest_appreciating_asset?.key || 'liquid_cash')}"></div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_fastest_growing_category"></div>
              <div class="asset-summary-value" style="font-size:1.35rem; color:var(--text-primary);" data-i18n="${_wealthComponentTitle(summary.fastest_growing_asset_category?.key || 'liquid_cash')}"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="alert alert-info" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="${insightKey}"></span>
    </div>
  `;

  applyTranslations();
  _drawWealthGrowthChart(payload);
  _attachWealthGrowthThemeListener();
}

async function loadWealthGrowthForecast(force = false) {
  if (_wealthGrowthForecastData && !force) {
    _renderWealthGrowthForecast(_wealthGrowthForecastData);
    _wealthGrowthForecastLoaded = true;
    return;
  }

  _renderWealthGrowthLoading();
  try {
    const response = await fetch("/api/financial-advisor/wealth-growth-forecast/");
    if (!response.ok) {
      throw new Error("wealth_growth_fetch_failed");
    }
    const payload = await response.json();
    _wealthGrowthForecastData = payload;
    _renderWealthGrowthForecast(payload);
    _wealthGrowthForecastLoaded = true;
  } catch (error) {
    _renderWealthGrowthError();
  }
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
    { key: "cash_flow_card_next_month", value: cp.next_month || 0 },
    { key: "cash_flow_card_month_3", value: cp.month_3 || 0 },
    { key: "cash_flow_card_month_6", value: cp.month_6 || 0 },
    { key: "cash_flow_card_month_12", value: cp.month_12 || 0 },
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
  const primaryTabs = FINANCIAL_ADVISOR_TABS.filter((tab) => FINANCIAL_ADVISOR_PRIMARY_TAB_IDS.includes(tab.id));
  const overflowTabs = FINANCIAL_ADVISOR_TABS.filter((tab) => !FINANCIAL_ADVISOR_PRIMARY_TAB_IDS.includes(tab.id));
  const overflowHasActive = overflowTabs.some((tab) => tab.id === activeTabId);

  const renderTabButton = (tab, cssClass) => `
    <button
      class="${cssClass} ${tab.id === activeTabId ? "active" : ""}"
      id="fa-tab-${tab.id}"
      data-bs-toggle="pill"
      data-bs-target="#fa-pane-${tab.id}"
      type="button"
      role="tab"
      aria-controls="fa-pane-${tab.id}"
      aria-selected="${tab.id === activeTabId ? "true" : "false"}"
      data-i18n="${tab.shortKey || tab.key}"
    ></button>
  `;

  const primaryTabsNav = primaryTabs.map((tab) => renderTabButton(tab, "financial-advisor-tab")).join("");
  const overflowTabsNav = overflowTabs.map((tab) => renderTabButton(tab, "financial-advisor-dropdown-item")).join("");

  const tabsContent = FINANCIAL_ADVISOR_TABS.map((tab, index) => `
    <div
      class="tab-pane fade ${tab.id === activeTabId ? "show active" : ""}"
      id="fa-pane-${tab.id}"
      role="tabpanel"
      aria-labelledby="fa-tab-${tab.id}"
      tabindex="0"
    >
        ${tab.id === "wealth-growth-forecast" ? `
        <div id="fa-wealth-growth-content"></div>
        ` : ""}
      ${tab.id === "cash-flow-forecast" ? `
      <div id="fa-cash-flow-content"></div>
      ` : `
        ${tab.id === "wealth-growth-forecast" ? "" : `
      <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
        <div class="card-body" style="padding:24px;">
          <h5 style="color:var(--text-primary); margin-bottom:10px;" data-i18n="financial_advisor_feature_coming_soon"></h5>
          <p style="color:var(--text-secondary); margin:0;" data-i18n="financial_advisor_next_phase_description"></p>
        </div>
      </div>
        `}
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
        <div class="financial-advisor-tabs-shell">
          <div class="financial-advisor-tabs-row" id="financialAdvisorTabs" role="tablist">
            <div class="financial-advisor-main-tabs">
              ${primaryTabsNav}
            </div>
            <div class="financial-advisor-more-wrap ${overflowHasActive ? "active" : ""}" id="financialAdvisorMoreWrap">
              <button
                class="financial-advisor-tab financial-advisor-more-toggle ${overflowHasActive ? "active" : ""}"
                id="financialAdvisorMoreBtn"
                type="button"
                aria-haspopup="true"
                aria-expanded="false"
              >
                <span data-i18n="financial_advisor_tab_more"></span>
                <i class="bi bi-chevron-down financial-advisor-more-icon"></i>
              </button>
              <div class="financial-advisor-more-menu" id="financialAdvisorMoreMenu" role="menu">
                ${overflowTabsNav}
              </div>
            </div>
          </div>
        </div>
        <div class="tab-content" id="financialAdvisorTabsContent">
          ${tabsContent}
        </div>
      </div>
    </div>
  `;

  applyTranslations();

  const tabsContainer = document.getElementById("financialAdvisorTabs");
  const moreWrap = document.getElementById("financialAdvisorMoreWrap");
  const moreBtn = document.getElementById("financialAdvisorMoreBtn");
  const moreMenu = document.getElementById("financialAdvisorMoreMenu");

  const closeMoreMenu = () => {
    if (!moreWrap || !moreBtn) return;
    moreWrap.classList.remove("open");
    moreBtn.setAttribute("aria-expanded", "false");
  };

  const positionMoreMenu = () => {
    if (!moreMenu) return;
    moreMenu.classList.remove("align-right", "align-left");
    const rect = moreMenu.getBoundingClientRect();
    const viewportPadding = 12;

    if (rect.right > (window.innerWidth - viewportPadding)) {
      moreMenu.classList.add("align-right");
      return;
    }

    if (rect.left < viewportPadding) {
      moreMenu.classList.add("align-left");
    }
  };

  const openMoreMenu = () => {
    if (!moreWrap || !moreBtn) return;
    moreWrap.classList.add("open");
    moreBtn.setAttribute("aria-expanded", "true");
    window.requestAnimationFrame(positionMoreMenu);
  };

  const syncMoreActiveState = () => {
    if (!moreWrap || !moreBtn) return;
    const hasOverflowActive = overflowTabs.some((tab) => {
      const tabButton = document.getElementById(`fa-tab-${tab.id}`);
      return tabButton?.classList.contains("active");
    });
    moreWrap.classList.toggle("active", hasOverflowActive);
    moreBtn.classList.toggle("active", hasOverflowActive);
  };

  if (_financialAdvisorMenuEventsAbortController) {
    _financialAdvisorMenuEventsAbortController.abort();
  }
  _financialAdvisorMenuEventsAbortController = new AbortController();
  const menuEventsSignal = _financialAdvisorMenuEventsAbortController.signal;

  if (moreBtn && moreWrap && moreMenu) {
    moreBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      if (moreWrap.classList.contains("open")) {
        closeMoreMenu();
      } else {
        openMoreMenu();
      }
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!moreWrap.contains(target)) {
        closeMoreMenu();
      }
    }, { signal: menuEventsSignal });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMoreMenu();
      }
    }, { signal: menuEventsSignal });

    window.addEventListener("resize", () => {
      if (moreWrap.classList.contains("open")) {
        positionMoreMenu();
      }
    }, { signal: menuEventsSignal });

    moreMenu.querySelectorAll('[data-bs-toggle="pill"]').forEach((menuTab) => {
      menuTab.addEventListener("click", () => {
        closeMoreMenu();
      });
    });
  }

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
        } else if (targetSelector === "#fa-pane-wealth-growth-forecast") {
          loadWealthGrowthForecast();
        }
        closeMoreMenu();
        syncMoreActiveState();
      });
    });
  }

  syncMoreActiveState();

  if (activeTabId === "cash-flow-forecast") {
    loadCashFlowForecast();
  } else if (activeTabId === "wealth-growth-forecast") {
    loadWealthGrowthForecast();
  }
}

window.renderFinancialAdvisor = renderFinancialAdvisor;
