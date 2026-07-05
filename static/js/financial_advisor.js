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

function renderFinancialAdvisor() {
  const main = document.getElementById("main-content");
  if (!main) return;

  const tabsNav = FINANCIAL_ADVISOR_TABS.map((tab, index) => `
    <button
      class="settings-tab ${index === 0 ? "active" : ""}"
      id="fa-tab-${tab.id}"
      data-bs-toggle="pill"
      data-bs-target="#fa-pane-${tab.id}"
      type="button"
      role="tab"
      aria-controls="fa-pane-${tab.id}"
      aria-selected="${index === 0 ? "true" : "false"}"
      data-i18n="${tab.key}"
    ></button>
  `).join("");

  const tabsContent = FINANCIAL_ADVISOR_TABS.map((tab, index) => `
    <div
      class="tab-pane fade ${index === 0 ? "show active" : ""}"
      id="fa-pane-${tab.id}"
      role="tabpanel"
      aria-labelledby="fa-tab-${tab.id}"
      tabindex="0"
    >
      <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
        <div class="card-body" style="padding:24px;">
          <h5 style="color:var(--text-primary); margin-bottom:10px;" data-i18n="financial_advisor_feature_coming_soon"></h5>
          <p style="color:var(--text-secondary); margin:0;" data-i18n="financial_advisor_next_phase_description"></p>
        </div>
      </div>
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
}

window.renderFinancialAdvisor = renderFinancialAdvisor;
