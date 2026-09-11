"use strict";

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");

  const canSalary = canAccessAny(["employment", "salary", "companies", "all_companies"]);
  const canDashboard = canAccessAny(["dashboard"]);
  const canAI = canAccessAny(["ai", "wealthflow_ai", "financial_advisor"]);
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
  const canSettings = canAccessAny(["settings", "user_management"]);

  const showWelcomeOnly = shouldShowWelcomeOnly();

  sidebar.innerHTML = `
        <div class="sidebar-brand">
            <div class="brand-icon"><i class="bi bi-bullseye"></i></div>
            <div class="brand-text">
                <span data-i18n="app_title">WealthFlow</span>
            </div>
        </div>
        <nav class="sidebar-nav">

            ${
              showWelcomeOnly
                ? `
            <button class="nav-item" data-route="welcome" onclick="navigate('welcome')">
                <i class="bi bi-house-heart"></i>
                <span data-i18n="welcome_page_nav">Welcome</span>
            </button>`
                : ""
            }

            ${
              !showWelcomeOnly && canDashboard
                ? `
            <button class="nav-item" onclick="navigate('dashboard')">
                <i class="bi bi-speedometer2"></i>
                <span data-i18n="nav_dashboard">Dashboard</span>
            </button>`
                : ""
            }

            ${
              !showWelcomeOnly && canAI
                ? `
            <button class="nav-item" data-route="ai" onclick="navigate('ai')">
                <i class="bi bi-cpu"></i>
                <span data-i18n="nav_wealthflow_ai">WealthFlow AI</span>
            </button>`
                : ""
            }

            ${
              !showWelcomeOnly && canFinancialAdvisor
                ? `
            <button class="nav-item" onclick="navigate('financial-advisor')">
                <i class="bi bi-graph-up-arrow"></i>
                <span data-i18n="nav_financial_advisor">Financial Advisor</span>
            </button>`
                : ""
            }

            <!-- Employment navigation item -->
            ${
              !showWelcomeOnly && canSalary
                ? `
            <button class="nav-item" data-route="employment" onclick="navigate('employment')">
                <i class="bi bi-briefcase"></i>
                <span data-i18n="nav_employment">Employment</span>
            </button>`
                : ""
            }

            ${!showWelcomeOnly ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

            ${
              !showWelcomeOnly && canBalance
                ? `
            <button class="nav-item" onclick="navigate('balance')">
                <i class="bi bi-wallet2"></i>
                <span data-i18n="nav_balance">Balance</span>
            </button>`
                : ""
            }
            ${
              !showWelcomeOnly && canBankCertificates
                ? `
            <button class="nav-item" onclick="navigate('bank-certificates')">
                <i class="bi bi-file-earmark-text"></i>
                <span data-i18n="nav_bank_certificates">Bank Certificates</span>
            </button>`
                : ""
            }
            ${
              !showWelcomeOnly && canFixedAssets
                ? `
            <button class="nav-item" onclick="navigate('fixed-assets')">
                <i class="bi bi-house-door"></i>
                <span data-i18n="nav_fixed_assets">Fixed Assets</span>
            </button>`
                : ""
            }
            ${
              !showWelcomeOnly && canExchangeRates
                ? `
            <button class="nav-item" onclick="navigate('exchange-rates')">
                <i class="bi bi-currency-exchange"></i>
                <span data-i18n="nav_exchange_rates">Exchange Rates</span>
            </button>`
                : ""
            }
            ${
              !showWelcomeOnly && canGoldPrice
                ? `
            <button class="nav-item" onclick="navigate('gold-price')">
                <i class="bi bi-brilliance"></i>
                <span data-i18n="nav_gold_price">Gold Price</span>
            </button>`
                : ""
            }

            ${!showWelcomeOnly && (canExpenses || canExpenseCategories || canReports || canAdvancedReports) ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

            <!-- Expenses & Reports section -->
            ${
              !showWelcomeOnly &&
              (canExpenses || canExpenseCategories || canReports || canAdvancedReports)
                ? `
            <div class="nav-section-header" onclick="toggleSection(this)"
                 style="cursor:pointer;padding:10px;display:flex;justify-content:space-between">
                <span data-i18n="nav_expenses_reports">Expenses Reports</span>
                <i class="bi bi-chevron-down chevron-icon"></i>
            </div>
            <div class="nav-section-content">
                ${
                  canExpenses
                    ? `
                <button class="nav-item" onclick="navigate('expenses')">
                    <i class="bi bi-receipt"></i>
                    <span data-i18n="nav_expenses">Expenses</span>
                </button>`
                    : ""
                }
                ${
                  canExpenseCategories
                    ? `
                <button class="nav-item" onclick="navigate('expense-categories')">
                    <i class="bi bi-tag"></i>
                    <span data-i18n="nav_expense_categories">Categories</span>
                </button>`
                    : ""
                }
                ${
                  canReports
                    ? `
                <button class="nav-item" onclick="navigate('reports')">
                    <i class="bi bi-graph-up"></i>
                    <span data-i18n="nav_expenses_report">Expenses Report</span>
                </button>`
                    : ""
                }
                ${
                  canAdvancedReports
                    ? `
                <button class="nav-item" onclick="navigate('advanced-reports')">
                    <i class="bi bi-bar-chart-line"></i>
                    <span data-i18n="nav_advanced_reports">Advanced Reports</span>
                </button>`
                    : ""
                }
            </div>`
                : ""
            }

            ${!showWelcomeOnly && canSettings ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

            ${
              !showWelcomeOnly && canSettings
                ? `
            <button class="nav-item" onclick="navigate('settings-languages')">
                <i class="bi bi-gear"></i>
                <span data-i18n="nav_settings">Settings</span>
            </button>`
                : ""
            }

        </nav>`;

  _renderSidebarFooter(sidebar);
  applyTranslations();
}

