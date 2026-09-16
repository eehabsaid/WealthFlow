"use strict";
// Sidebar primary nav items: welcome/dashboard/AI/financial-advisor/employment.
// Split out of renderSidebar (200-line rule). Do not edit directly.

function buildSidebarPrimaryNavHtml(
  showWelcomeOnly,
  canDashboard,
  canAI,
  canFinancialAdvisor,
  canSalary
) {
  return `${
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

            `;
}
