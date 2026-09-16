"use strict";
// Sidebar expenses & reports nav section: divider + collapsible section.
// Split out of renderSidebar (200-line rule). Do not edit directly.

function buildSidebarExpensesReportsNavHtml(
  showWelcomeOnly,
  canExpenses,
  canExpenseCategories,
  canReports,
  canAdvancedReports
) {
  return `${!showWelcomeOnly && (canExpenses || canExpenseCategories || canReports || canAdvancedReports) ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

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

            `;
}
