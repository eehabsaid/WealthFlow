"use strict";
// Sidebar permission checks + orchestration. Nav section fragments split
// into nav_primary.js, nav_modules.js, nav_expenses_reports.js, and
// nav_settings.js (200-line rule). Do not edit directly.

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");

  const canSalary = canAccessAny(["employment", "salary", "companies", "all_companies"]);
  const canDashboard = canAccessAny(["dashboard"]);
  const canAI =
    canAccessAny(["ai", "wealthflow_ai", "financial_advisor"]) && planAllowsAIWorkspace();
  const canFinancialAdvisor = canAccessAny(["financial_advisor"]);
  const canBalance = canAccessAny(["balance", "banks"]);
  const canBankCertificates = canAccessAny(["bank_certificates"]);
  const canFixedAssets = canAccessAny(["fixed_assets"]);
  const canExchangeRates = canAccessAny(["exchange_rates", "currencies"]);
  const canGoldPrice = canAccessAny(["gold_price"]);
  const canExpenses = canAccessAny(["expenses"]);
  const canExpenseCategories = canAccessAny(["expense-categories"]);
  const canReports = canAccessAny(["reports"]);
  const canAdvancedReports = canAccessAny(["advanced_reports"]);
  const canSettings =
    isPrivilegedUser() ||
    (_allowedPages || []).some((k) => k === "settings" || k.startsWith("settings_"));

  const showWelcomeOnly = shouldShowWelcomeOnly();

  sidebar.innerHTML = `
        <div class="sidebar-brand">
            <div class="brand-icon"><i class="bi bi-bullseye"></i></div>
            <div class="brand-text">
                <span data-i18n="app_title">WealthFlow</span>
            </div>
        </div>
        <nav class="sidebar-nav">

            ${buildSidebarPrimaryNavHtml(showWelcomeOnly, canDashboard, canAI, canFinancialAdvisor, canSalary)}${buildSidebarModulesNavHtml(showWelcomeOnly, canBalance, canBankCertificates, canFixedAssets, canExchangeRates, canGoldPrice)}${buildSidebarExpensesReportsNavHtml(showWelcomeOnly, canExpenses, canExpenseCategories, canReports, canAdvancedReports)}${buildSidebarSettingsNavHtml(showWelcomeOnly, canSettings)}        </nav>`;

  _renderSidebarFooter(sidebar);
  applyTranslations();
}
