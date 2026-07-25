'use strict';

function renderTopbar() {
    const topbar = document.getElementById('topbar');
    topbar.innerHTML = `
        <button id="mobile-nav-trigger" class="btn d-lg-none p-2 me-2" style="color:var(--text-primary)"
                onclick="toggleMobileSidebar()"
                style="font-size:20px;border:none;background:transparent">
            <i class="bi bi-list"></i>
        </button>
        <div id="breadcrumb" style="font-weight:600;font-size:14px;color:var(--text-secondary)"></div>
        <div style="display:flex;align-items:center;gap:12px">
            <button id="desktop-sidebar-mode-btn" class="btn-icon" onclick="toggleSidebarDesktopMode()" title="Sidebar Mode">
                <i class="bi bi-layout-sidebar-inset"></i>
            </button>
            <button id="themeToggleBtn" onclick="toggleTheme()"
                style="background:var(--bg-tertiary);border:1px solid var(--border-color);
                       cursor:pointer;font-size:18px;color:var(--text-primary);
                       padding:4px 8px;border-radius:8px;line-height:1;
                       transition:opacity .15s"
                title="Toggle light/dark theme">
                🌙
            </button>
            <div class="dropdown">
                <button class="btn-icon dropdown-toggle" data-bs-toggle="dropdown" id="langBtn">
                    🌐 <span id="langLabel">EN</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end" id="langMenu"
                    style="background:var(--bg-secondary);border:1px solid var(--border-color)">
                </ul>
            </div>
            <button class="btn-primary-custom" id="addEntryBtn"
                    onclick="triggerAddEntry()" style="display:none">
                <i class="bi bi-plus-lg"></i> <span data-i18n="btn_add">Add</span>
            </button>
        </div>`;
    loadLangMenu();
    updateSidebarModeButton();
}

async function loadLangMenu() {
    try {
        const res  = await fetch('/api/settings/');
        const data = await res.json();
        const langs = JSON.parse(data.settings.available_languages || '[]');
        const menu  = document.getElementById('langMenu');
        if (!menu) return;
        menu.innerHTML = langs.map(l => `
            <li><a class="dropdown-item" href="#"
                   style="color:var(--text-primary)"
                   onclick="loadLanguage('${l.code}');
                            document.getElementById('langLabel').textContent='${l.code.toUpperCase()}';
                            return false">
                ${l.label}
            </a></li>`).join('');
        const active = data.settings.active_language || 'en';
        const el = document.getElementById('langLabel');
        if (el) el.textContent = active.toUpperCase();
    } catch (e) {}
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// ROUTING
// ════════════════════════════════════════════════════════════════════════════

// Route definitions: hash → { i18nKey, addBtn, render }
const ROUTES = {
    'dashboard':          { key: 'nav_dashboard',         add: false, fn: () => renderDashboard()     },
    'financial-advisor':  { key: 'nav_financial_advisor', add: false, fn: () => renderFinancialAdvisor() },
    'balance':            { key: 'nav_balance',           add: false, fn: () => renderBalance()       },
    'bank-certificates':  { key: 'nav_bank_certificates', add: true,  fn: () => renderBankCertificates() },
    'employment':         { key: 'nav_employment',        add: true,  fn: () => renderEmploymentPage() },
    'salary':             { key: 'nav_employment',        add: true,  fn: () => renderEmploymentPage() },
    'exchange-rates':     { key: 'nav_exchange_rates',    add: false, fn: () => renderExchangeRates() },
    'gold-price':         { key: 'nav_gold_price',        add: false, fn: () => renderGoldPrice()     },
    'expenses':           { key: 'nav_expenses',          add: false, fn: () => renderExpenses()      },
    'expense-categories': { key: 'nav_expense_categories', add: false, fn: () => renderExpenseCategories() },
    'reports':            { key: 'nav_expenses_report',   add: false, fn: () => renderReports()       },
    'advanced-reports':   { key: 'nav_advanced_reports',  add: false, fn: () => renderAdvancedReports() },
    'fixed-assets':       { key: 'nav_fixed_assets',      add: false,  fn: () => renderFixedAssets() },
};

