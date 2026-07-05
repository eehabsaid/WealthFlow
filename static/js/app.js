// app.js — Application bootstrap, routing, sidebar, modals, toasts, utilities

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

let _companies   = [];
let _banks       = [];
let _activeRoute = '';
let _allowedPages = [];

window.translations = {};

// ════════════════════════════════════════════════════════════════════════════
// BOOTSTRAP
// ════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    applyStoredTheme();
    await loadLanguage(localStorage.getItem('lang') || 'en');
    await initApp();
    window.addEventListener('hashchange', route);
    route();
});

document.addEventListener('languageChanged', () => {
    if (typeof route === 'function') {
        route();
    }
});

async function initApp() {
    const [cRes, bRes, meRes, profileRes] = await Promise.all([
        fetch('/api/companies/'),
        fetch('/api/banks/'),
        fetch('/api/auth/me/'),
        fetch('/api/auth/profile/'),
    ]);

    const [cData, bData, meData, pData] = await Promise.all([
        cRes.json(), bRes.json(), meRes.json(), profileRes.json(),
    ]);

    _companies = cData.companies || [];
    _banks     = bData.banks     || [];
    _allowedPages = meData.allowed_pages || [];

    // Merge user info from both endpoints
    window._currentUser = { ...meData.user, ...pData.profile };

    renderSidebar();
    renderTopbar();

    // Check reminders in background after load
    setTimeout(() => {
        if (typeof checkReminders === 'function') checkReminders();
    }, 2000);
}

function isPrivilegedUser() {
    const u = window._currentUser || {};
    return !!(u.is_staff || u.is_superuser);
}

function canAccessAny(requiredKeys) {
    if (isPrivilegedUser()) {
        return true;
    }
    const allowed = new Set(_allowedPages || []);
    return requiredKeys.some((key) => allowed.has(key));
}

function hasAnyAssignedPageAccess() {
    if (isPrivilegedUser()) {
        return true;
    }
    return (_allowedPages || []).length > 0;
}

function shouldShowWelcomeOnly() {
    return !hasAnyAssignedPageAccess();
}

function permissionToRoute(pageKey) {
    if (pageKey === 'dashboard') return 'dashboard';
    if (pageKey === 'balance') return 'balance';
    if (pageKey === 'bank_certificates') return 'bank-certificates';
    if (pageKey === 'fixed_assets') return 'fixed-assets';
    if (pageKey === 'all_companies' || pageKey === 'salary') return 'all-companies';
    if (pageKey === 'exchange_rates') return 'exchange-rates';
    if (pageKey === 'gold_price') return 'gold-price';
    if (pageKey === 'expenses') return 'expenses';
    if (pageKey === 'expense-categories') return 'expense-categories';
    if (pageKey === 'reports') return 'reports';
    if (pageKey === 'advanced_reports') return 'advanced-reports';
    if (pageKey === 'settings') return 'settings-languages';
    if (pageKey === 'user_management') return 'settings-users';
    return '';
}

function routeAllowed(hash) {
    if (isPrivilegedUser()) {
        return true;
    }
    if (hash === 'welcome') {
        return shouldShowWelcomeOnly();
    }
    if (hash === 'dashboard') {
        return canAccessAny(['dashboard']);
    }
    if (hash === 'balance') {
        return canAccessAny(['balance']);
    }
    if (hash === 'bank-certificates') {
        return canAccessAny(['bank_certificates']);
    }
    if (hash === 'fixed-assets') {
        return canAccessAny(['fixed_assets']);
    }
    if (hash === 'all-companies') {
        return canAccessAny(['all_companies', 'salary']);
    }
    if (hash.startsWith('salary-')) {
        return canAccessAny(['salary']);
    }
    if (hash === 'exchange-rates') {
        return canAccessAny(['exchange_rates']);
    }
    if (hash === 'gold-price') {
        return canAccessAny(['gold_price']);
    }
    if (hash === 'expenses') {
        return canAccessAny(['expenses']);
    }
    if (hash === 'expense-categories') {
        return canAccessAny(['expense-categories']);
    }
    if (hash === 'reports') {
        return canAccessAny(['reports']);
    }
    if (hash === 'advanced-reports') {
        return canAccessAny(['advanced_reports']);
    }
    if (hash.startsWith('settings')) {
        return canAccessAny(['settings', 'user_management']);
    }
    return false;
}

function getFirstAllowedRoute() {
    if (isPrivilegedUser()) {
        return 'dashboard';
    }

    // For normal users, homepage should be one of the assigned pages.
    for (const pageKey of (_allowedPages || [])) {
        const route = permissionToRoute(pageKey);
        if (route && routeAllowed(route)) {
            return route;
        }
    }

    const candidates = ['dashboard', 'balance', 'bank-certificates', 'fixed-assets', 'all-companies', 'exchange-rates', 'gold-price', 'expenses', 'expense-categories', 'reports', 'advanced-reports', 'settings-languages'];
    for (const candidate of candidates) {
        if (routeAllowed(candidate)) {
            return candidate;
        }
    }
    return 'welcome';
}

function renderWelcomePage() {
    const main = document.getElementById('main-content');
    if (!main) {
        return;
    }
    main.innerHTML = `
        <div style="min-height:60vh;display:flex;align-items:center;justify-content:center;padding:24px;">
            <div style="max-width:760px;width:100%;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:14px;padding:28px;">
                <div style="font-size:26px;font-weight:800;color:var(--text-primary);margin-bottom:10px;" data-i18n="welcome_page_title">Welcome to WealthFlow</div>
                <div style="font-size:14px;color:var(--text-secondary);line-height:1.8;" data-i18n="welcome_page_message">Your account is active, but no page permissions are assigned yet. Please contact your administrator to grant access from Manage Permissions.</div>
            </div>
        </div>
    `;
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ════════════════════════════════════════════════════════════════════════════

function renderSidebar() {
    const sidebar = document.getElementById('sidebar');

    const companyItems = _companies.map(c => `
        <button class="nav-item" data-route="salary-${c.id}" onclick="navigate('salary-${c.id}')">
            <span class="nav-dot" style="background:${c.color_hex}"></span>
            <span>${c.display_name}</span>
        </button>`).join('');

    const canSalary = canAccessAny(['salary']);
    const canDashboard = canAccessAny(['dashboard']);
    const canBalance = canAccessAny(['balance']);
    const canBankCertificates = canAccessAny(['bank_certificates']);
    const canFixedAssets = canAccessAny(['fixed_assets']);
    const canExchangeRates = canAccessAny(['exchange_rates']);
    const canGoldPrice = canAccessAny(['gold_price']);
    const canExpenses = canAccessAny(['expenses']);
    const canExpenseCategories = canAccessAny(['expense-categories']);
    const canReports = canAccessAny(['reports']);
    const canAdvancedReports = canAccessAny(['advanced_reports']);
    const canSettings = canAccessAny(['settings', 'user_management']);

    const showWelcomeOnly = shouldShowWelcomeOnly();

    sidebar.innerHTML = `
        <div class="sidebar-brand">
            <div class="brand-icon">💰</div>
            <div class="brand-text">
                <span data-i18n="app_title">WealthFlow</span>
            </div>
        </div>
        <nav class="sidebar-nav">

            ${showWelcomeOnly ? `
            <button class="nav-item" data-route="welcome" onclick="navigate('welcome')">
                <i class="bi bi-house-heart"></i>
                <span data-i18n="welcome_page_nav">Welcome</span>
            </button>` : ''}

            ${!showWelcomeOnly && canDashboard ? `
            <button class="nav-item" onclick="navigate('dashboard')">
                <i class="bi bi-speedometer2"></i>
                <span data-i18n="nav_dashboard">Dashboard</span>
            </button>` : ''}

            <!-- Salary section -->
            ${!showWelcomeOnly && canSalary ? `
            <div class="nav-section-header" onclick="toggleSection(this)"
                 style="cursor:pointer;padding:10px;display:flex;justify-content:space-between">
                <span data-i18n="nav_salary">Salary</span>
                <i class="bi bi-chevron-down chevron-icon"></i>
            </div>
            <div class="nav-section-content">
                ${companyItems}
                <button class="nav-item" onclick="navigate('all-companies')">
                    <i class="bi bi-building"></i>
                    <span data-i18n="nav_all_companies">All Companies</span>
                </button>
            </div>` : ''}

            ${!showWelcomeOnly ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ''}

            ${!showWelcomeOnly && canBalance ? `
            <button class="nav-item" onclick="navigate('balance')">
                <i class="bi bi-wallet2"></i>
                <span data-i18n="nav_balance">Balance</span>
            </button>` : ''}
            ${!showWelcomeOnly && canBankCertificates ? `
            <button class="nav-item" onclick="navigate('bank-certificates')">
                <i class="bi bi-file-earmark-text"></i>
                <span data-i18n="nav_bank_certificates">Bank Certificates</span>
            </button>` : ''}
            ${!showWelcomeOnly && canFixedAssets ? `
            <button class="nav-item" onclick="navigate('fixed-assets')">
                <i class="bi bi-house-door"></i>
                <span data-i18n="nav_fixed_assets">Fixed Assets</span>
            </button>` : ''}
            ${!showWelcomeOnly && canExchangeRates ? `
            <button class="nav-item" onclick="navigate('exchange-rates')">
                <i class="bi bi-currency-exchange"></i>
                <span data-i18n="nav_exchange_rates">Exchange Rates</span>
            </button>` : ''}
            ${!showWelcomeOnly && canGoldPrice ? `
            <button class="nav-item" onclick="navigate('gold-price')">
                <i class="bi bi-brilliance"></i>
                <span data-i18n="nav_gold_price">Gold Price</span>
            </button>` : ''}

            ${!showWelcomeOnly && (canExpenses || canExpenseCategories || canReports || canAdvancedReports) ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ''}

            <!-- Expenses & Reports section -->
            ${!showWelcomeOnly && (canExpenses || canExpenseCategories || canReports || canAdvancedReports) ? `
            <div class="nav-section-header" onclick="toggleSection(this)"
                 style="cursor:pointer;padding:10px;display:flex;justify-content:space-between">
                <span data-i18n="nav_expenses_reports">Expenses &amp; Reports</span>
                <i class="bi bi-chevron-down chevron-icon"></i>
            </div>
            <div class="nav-section-content">
                ${canExpenses ? `
                <button class="nav-item" onclick="navigate('expenses')">
                    <i class="bi bi-receipt"></i>
                    <span data-i18n="nav_expenses">Expenses</span>
                </button>` : ''}
                ${canExpenseCategories ? `
                <button class="nav-item" onclick="navigate('expense-categories')">
                    <i class="bi bi-tag"></i>
                    <span data-i18n="nav_expense_categories">Categories</span>
                </button>` : ''}
                ${canReports ? `
                <button class="nav-item" onclick="navigate('reports')">
                    <i class="bi bi-graph-up"></i>
                    <span data-i18n="nav_reports">Reports</span>
                </button>` : ''}
                ${canAdvancedReports ? `
                <button class="nav-item" onclick="navigate('advanced-reports')">
                    <i class="bi bi-bar-chart-line"></i>
                    <span data-i18n="nav_advanced_reports">Advanced Reports</span>
                </button>` : ''}
            </div>` : ''}

            ${!showWelcomeOnly && canSettings ? '<div style="border-top:1px solid var(--border-color);margin:10px 0"></div>' : ''}

            ${!showWelcomeOnly && canSettings ? `
            <button class="nav-item" onclick="navigate('settings-languages')">
                <i class="bi bi-gear"></i>
                <span data-i18n="nav_settings">Settings</span>
            </button>` : ''}

        </nav>`;

    _renderSidebarFooter(sidebar);
    applyTranslations();
}

function _renderSidebarFooter(sidebar) {
    const u      = window._currentUser || {};
    const uName  = u.display_name || u.full_name || u.username || 'Guest';
    const avatar = u.avatar_url
        ? `<img src="${u.avatar_url}"
               style="width:36px;height:36px;border-radius:50%;object-fit:cover;
                      border:2px solid var(--border-color);flex-shrink:0">`
        : `<div style="width:36px;height:36px;border-radius:50%;
                       background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                       display:flex;align-items:center;justify-content:center;
                       font-size:15px;font-weight:700;color:#fff;flex-shrink:0">
               ${uName.charAt(0).toUpperCase()}
           </div>`;

    const nav = sidebar.querySelector('.sidebar-nav');
    if (!nav) return;

    // Remove existing footer to prevent duplicates
    const old = nav.querySelector('.user-sidebar-footer');
    if (old) old.remove();

    const footer = document.createElement('div');
    footer.className  = 'user-sidebar-footer';
    footer.style.cssText = 'border-top:1px solid var(--border-color);padding:10px 8px 8px;margin-top:auto';
    footer.innerHTML  = `
        <div style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;
                    cursor:pointer;transition:background .15s"
             onclick="window.showProfileModal && window.showProfileModal()"
             onmouseenter="this.style.background='var(--bg-tertiary)'"
             onmouseleave="this.style.background='transparent'"
             title="${t('click_to_edit_profile', 'Edit profile')}">
            ${avatar}
            <div style="overflow:hidden;flex:1;min-width:0" class="nav-text">
                <div style="font-size:13px;font-weight:600;color:var(--text-primary);
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    ${uName}
                </div>
                <div style="font-size:11px;color:var(--text-muted)">${u.email || ''}</div>
            </div>
            <i class="bi bi-pencil-square nav-text"
               style="color:var(--text-muted);font-size:13px;flex-shrink:0"></i>
        </div>
        <button onclick="window.doLogout && window.doLogout()"
                style="width:100%;display:flex;align-items:center;gap:9px;padding:8px 12px;
                       border:none;background:none;color:var(--accent-red,#ff4d6d);cursor:pointer;
                       border-radius:8px;font-size:13.5px;font-weight:600;
                       transition:background .15s;margin-top:2px"
                onmouseenter="this.style.background='rgba(255,77,109,0.1)'"
                onmouseleave="this.style.background='none'">
            <i class="bi bi-box-arrow-left" style="font-size:16px"></i>
            <span class="nav-text" data-i18n="nav_logout">Logout</span>
        </button>`;
    nav.appendChild(footer);
}

// ════════════════════════════════════════════════════════════════════════════
// TOPBAR
// ════════════════════════════════════════════════════════════════════════════

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
    'balance':            { key: 'nav_balance',           add: true,  fn: () => renderBalance()       },
    'bank-certificates':  { key: 'nav_bank_certificates', add: true,  fn: () => renderBankCertificates() },
    'all-companies':      { key: 'nav_all_companies',     add: true,  fn: () => renderAllCompanies()  },
    'exchange-rates':     { key: 'nav_exchange_rates',    add: false, fn: () => renderExchangeRates() },
    'gold-price':         { key: 'nav_gold_price',        add: false, fn: () => renderGoldPrice()     },
    'expenses':           { key: 'nav_expenses_reports',  add: false, fn: () => renderExpenses()      },
    'expense-categories': { key: 'nav_expenses_reports',  add: false, fn: () => renderExpenseCategories() },
    'reports':            { key: 'nav_expenses_reports',  add: false, fn: () => renderReports()       },
    'advanced-reports':   { key: 'nav_expenses_reports',  add: false, fn: () => renderAdvancedReports() },
    'fixed-assets':       { key: 'nav_fixed_assets',      add: false,  fn: () => renderFixedAssets() },
};

function route() {
    const requested = window.location.hash.replace('#', '');
    const hash = requested || (shouldShowWelcomeOnly() ? 'welcome' : getFirstAllowedRoute());

    if (shouldShowWelcomeOnly() && hash !== 'welcome') {
        navigate('welcome');
        return;
    }

    if (!shouldShowWelcomeOnly() && hash === 'welcome') {
        navigate(getFirstAllowedRoute());
        return;
    }

    if (!routeAllowed(hash)) {
        const fallback = getFirstAllowedRoute();
        if (hash !== fallback) {
            navigate(fallback);
            return;
        }
    }

    _activeRoute = hash;

    // Highlight active nav item
    document.querySelectorAll('.nav-item').forEach(el =>
        el.classList.toggle('active', el.dataset.route === hash));

    const addBtn = document.getElementById('addEntryBtn');
    const bc     = document.getElementById('breadcrumb');

    if (ROUTES[hash]) {
        const r = ROUTES[hash];
        if (addBtn) addBtn.style.display = r.add ? 'inline-flex' : 'none';
        if (bc) { bc.setAttribute('data-i18n', r.key); bc.textContent = ''; }
        r.fn();

    } else if (hash === 'welcome') {
        if (addBtn) addBtn.style.display = 'none';
        if (bc) { bc.removeAttribute('data-i18n'); bc.textContent = t('welcome_page_nav', 'Welcome'); }
        renderWelcomePage();

    } else if (hash.startsWith('salary-')) {
        if (addBtn) addBtn.style.display = 'inline-flex';
        if (bc) { bc.setAttribute('data-i18n', 'nav_salary'); bc.textContent = ''; }
        renderSalaryPage(parseInt(hash.split('-')[1]));

    } else if (hash.startsWith('settings')) {
        if (addBtn) addBtn.style.display = 'none';
        if (bc) { bc.setAttribute('data-i18n', 'nav_settings'); bc.textContent = ''; }
        renderSettings(hash);
    }

    applyTranslations();
}

window.route = route;

function navigate(route) {
    window.location.hash = route;
    closeMobileSidebar();
    // Force hash re-trigger in case hash hasn't changed
    setTimeout(() => { window.location.hash = route; }, 50);
}

function triggerAddEntry() {
    const hash = window.location.hash.replace('#', '');
    if (hash.startsWith('salary-'))       showSalaryModal(null, parseInt(hash.split('-')[1]));
    else if (hash === 'balance')          showBalanceModal(null);
    else if (hash === 'bank-certificates') showBankCertificateModal(null);
    else if (hash === "fixed-assets") showFixedAssetModal();
    else if (hash === 'all-companies')    showCompanyModal(null);
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL
// ════════════════════════════════════════════════════════════════════════════

function showModal(html) {
    let el = document.getElementById('globalModal');
    if (!el) {
        el = document.createElement('div');
        el.id        = 'globalModal';
        el.className = 'modal fade modal-dark';
        el.setAttribute('tabindex', '-1');
        document.body.appendChild(el);
    }

    //<div class="modal-dialog modal-dialog-centered"> small dialog
    el.innerHTML = `
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">${html}</div>
        </div>`;
    bootstrap.Modal.getInstance(el)?.dispose();
    const modal = new bootstrap.Modal(el, {
        backdrop: 'static',
        keyboard: false,
    });
    modal.show();
}

function closeModal() {
    const el = document.getElementById('globalModal');
    if (el) bootstrap.Modal.getInstance(el)?.hide();
}

// ════════════════════════════════════════════════════════════════════════════
// TOAST
// ════════════════════════════════════════════════════════════════════════════

function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    const id        = 'toast-' + Date.now();
    const color     = type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)';
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast align-items-center" role="alert"
             style="border-left:3px solid ${color}">
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast"></button>
            </div>
        </div>`);
    new bootstrap.Toast(document.getElementById(id), { delay: 3000 }).show();
}

// ════════════════════════════════════════════════════════════════════════════
// NUMBER FORMATTERS
// ════════════════════════════════════════════════════════════════════════════

function getNumberLocale() {
    const currentLang = localStorage.getItem("lang") || "en";     
    // 'ar-EG-u-nu-arab' explicitly forces the localized Arabic-Indic digits (١, ٢, ٣)
    return currentLang === "ar" ? "ar-EG-u-nu-arab" : "en-US";
}

function fmt(n) {
    if (n === null || n === undefined) return '-';
    return Number(n).toLocaleString(getNumberLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 6 });
}

function fmtpresent(n) {
    if (n === null || n === undefined) return '-';
    return Number(n).toLocaleString(getNumberLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Rewritten into a super compact format to keep your file line-count ultra-low:
function fmtInt(n) { return (n === null || n === undefined) ? '-' : Number(n).toLocaleString(getNumberLocale()); }

function amtClass(n) {
    if (n > 0) return 'amt-negative';
    if (n < 0) return 'amt-positive';
    return 'amt-zero';
}

// ════════════════════════════════════════════════════════════════════════════
// LOADING HELPERS
// ════════════════════════════════════════════════════════════════════════════

function showLoading() {
    const el = document.querySelector('.spinner-overlay');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    const el = document.querySelector('.spinner-overlay');
    if (el) el.style.display = 'none';
}

function loadingHTML() {
    return `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Loading...</p>
        </div>`;
}

// ════════════════════════════════════════════════════════════════════════════
// MOBILE SIDEBAR
// ════════════════════════════════════════════════════════════════════════════

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const open    = sidebar.classList.toggle('open');
    overlay?.classList.toggle('show', open);
}

function closeMobileSidebar() {
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebarOverlay')?.classList.remove('show');
}

// ════════════════════════════════════════════════════════════════════════════
// SECTION TOGGLE (collapsible nav sections)
// ════════════════════════════════════════════════════════════════════════════

function toggleSection(el) {
    const content = el.nextElementSibling;
    const icon    = el.querySelector('.chevron-icon');
    const closed  = content.style.display === 'none';
    content.style.display = closed ? 'block' : 'none';
    icon?.classList.toggle('bi-chevron-down',  closed);
    icon?.classList.toggle('bi-chevron-right', !closed);
}

// ════════════════════════════════════════════════════════════════════════════
// AUTH — LOGOUT, PROFILE MODAL, AVATAR UPLOAD
// ════════════════════════════════════════════════════════════════════════════

function doLogout() {
    // Use GET redirect to the Django logout view (no CSRF token needed)
    window.location.href = '/accounts/logout/';
}

function showProfileModal() {
    const u        = window._currentUser || {};
    const name     = u.display_name || u.full_name || u.username || '';
    const initials = name ? name.charAt(0).toUpperCase() : '?';
    const avatar   = u.avatar_url
        ? `<img src="${u.avatar_url}" id="avatarPreview"
               style="width:90px;height:90px;border-radius:50%;object-fit:cover;
                      border:3px solid var(--border-color)">`
        : `<div id="avatarPreview"
               style="width:90px;height:90px;border-radius:50%;
                      background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                      display:inline-flex;align-items:center;justify-content:center;
                      font-size:36px;font-weight:700;color:#fff;
                      border:3px solid var(--border-color)">
               ${initials}
           </div>`;

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title">
                <i class="bi bi-person-circle" style="color:var(--accent-primary);margin-right:8px"></i>
                My Profile
            </h5>
            <button type="button" class="btn-close btn-close-white"
                    data-bs-dismiss="modal" onclick="closeModal()"></button>
        </div>
        <div class="modal-body">
            <div style="text-align:center;margin-bottom:22px">
                <div style="position:relative;display:inline-block">
                    ${avatar}
                    <label for="avatarInput"
                           style="position:absolute;bottom:2px;right:2px;
                                  background:var(--accent-primary);color:#fff;
                                  width:28px;height:28px;border-radius:50%;
                                  display:flex;align-items:center;justify-content:center;
                                  cursor:pointer;font-size:13px;border:2px solid var(--bg-secondary)"
                           title="Upload photo">
                        <i class="bi bi-camera"></i>
                    </label>
                    <input type="file" id="avatarInput" accept="image/*" style="display:none"
                           onchange="window.previewAndUploadAvatar(this)">
                </div>
                <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">
                    Click the camera icon to change your photo
                </div>
            </div>
            <div class="row g-3">
                <div class="col-12">
                    <label class="form-label">Full Name</label>
                    <input type="text" class="form-control" id="profileFullName"
                           value="${name}" placeholder="e.g. Ehab Mohamed">
                </div>
                <div class="col-12">
                    <label class="form-label">Username</label>
                    <input type="text" class="form-control"
                           value="${u.username || ''}" disabled style="opacity:.6">
                </div>
                <div class="col-12">
                    <label class="form-label">Email</label>
                    <input type="text" class="form-control"
                           value="${u.email || ''}" disabled style="opacity:.6">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal"
                    onclick="closeModal()">Cancel</button>
            <button class="btn-primary-custom" onclick="window.saveProfile()">
                <i class="bi bi-floppy"></i> Save
            </button>
        </div>`);
}

async function previewAndUploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;

    // Preview immediately
    const reader = new FileReader();
    reader.onload = e => {
        const prev = document.getElementById('avatarPreview');
        if (prev) prev.outerHTML = `<img id="avatarPreview" src="${e.target.result}"
            style="width:90px;height:90px;border-radius:50%;object-fit:cover;
                   border:3px solid var(--border-color)">`;
    };
    reader.readAsDataURL(file);

    // Upload
    const fd = new FormData();
    fd.append('avatar', file);
    try {
        const res  = await fetch('/api/auth/profile/avatar/', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) {
            if (window._currentUser) window._currentUser.avatar_url = data.avatar_url;
            showToast('Photo updated ✓');
            renderSidebar();
        } else {
            showToast('Upload failed: ' + (data.error || ''), 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

async function saveProfile() {
    const fullName = document.getElementById('profileFullName')?.value.trim() || '';
    try {
        const res  = await fetch('/api/auth/profile/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ full_name: fullName }),
        });
        const data = await res.json();
        if (res.ok) {
            if (window._currentUser) {
                window._currentUser.full_name    = data.profile.full_name;
                window._currentUser.display_name = data.profile.display_name;
            }
            closeModal();
            showToast('Profile saved ✓');
            renderSidebar();
        } else {
            showToast('Error: ' + (data.error || ''), 'error');
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// MISC HELPERS
// ════════════════════════════════════════════════════════════════════════════

function setBreadcrumb(title) {
    const bc = document.getElementById('breadcrumb');
    if (bc) bc.textContent = title;
}

// Legacy translation alias used by some modules
function translate(key) {
    const lang = localStorage.getItem('lang') || 'en';
    return window.translations?.[lang]?.[key] || key;
}

// ════════════════════════════════════════════════════════════════════════════
// THEME TOGGLE
// ════════════════════════════════════════════════════════════════════════════

function toggleTheme() {
    const html = document.documentElement;
    const isLight = html.getAttribute('data-theme') === 'light';
    const next    = isLight ? 'dark' : 'light';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    _updateThemeBtn(next);
}

function _updateThemeBtn(theme) {
    const btn = document.getElementById('themeToggleBtn');
    if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
}

function applyStoredTheme() {
    const stored = localStorage.getItem('theme') || 'dark';
    if (stored === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    _updateThemeBtn(stored);
}

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.navigate             = navigate;
window.showModal            = showModal;
window.closeModal           = closeModal;
window.showToast            = showToast;
window.fmt                  = fmt;
window.fmtpresent           = fmtpresent;
window.fmtInt               = fmtInt;
window.amtClass             = amtClass;
window.showLoading          = showLoading;
window.hideLoading          = hideLoading;
window.loadingHTML          = loadingHTML;
window.setBreadcrumb        = setBreadcrumb;
window.renderSidebar        = renderSidebar;
window.loadLangMenu         = loadLangMenu;
window.toggleMobileSidebar  = toggleMobileSidebar;
window.closeMobileSidebar   = closeMobileSidebar;
window.doLogout             = doLogout;
window.showProfileModal     = showProfileModal;
window.previewAndUploadAvatar = previewAndUploadAvatar;
window.saveProfile          = saveProfile;
window.getCompanies         = () => _companies;
window.getBanks             = () => _banks;
window.toggleTheme          = toggleTheme;
window.applyStoredTheme     = applyStoredTheme;
window.renderFixedAssets    = window.renderFixedAssets;
window.refreshBanks         = async () => {
    const r = await fetch('/api/banks/');
    _banks  = (await r.json()).banks || [];
};
window.refreshCompanies     = async () => {
    const r  = await fetch('/api/companies/');
    _companies = (await r.json()).companies || [];
};