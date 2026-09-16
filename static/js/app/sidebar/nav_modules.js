"use strict";
// Sidebar modules nav section: divider + balance/certs/fixed-assets/exchange-rates/gold-price.
// Split out of renderSidebar (200-line rule). Do not edit directly.

function buildSidebarModulesNavHtml(
  showWelcomeOnly,
  canBalance,
  canBankCertificates,
  canFixedAssets,
  canExchangeRates,
  canGoldPrice
) {
  return `${!showWelcomeOnly ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ""}

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

            `;
}
