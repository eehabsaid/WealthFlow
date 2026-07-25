'use strict';

function renderSidebar() {
    const sidebar = document.getElementById('sidebar');


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
            <div class="brand-icon"><i class="bi bi-bullseye"></i></div>
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

            ${!showWelcomeOnly ? `
            <button class="nav-item" onclick="navigate('financial-advisor')">
                <i class="bi bi-graph-up-arrow"></i>
                <span data-i18n="nav_financial_advisor">Financial Advisor</span>
            </button>` : ''}

            <!-- Employment navigation item -->
            ${!showWelcomeOnly && canSalary ? `
            <button class="nav-item" data-route="employment" onclick="navigate('employment')">
                <i class="bi bi-briefcase"></i>
                <span data-i18n="nav_employment">Employment</span>
            </button>` : ''}

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
                <span data-i18n="nav_expenses_reports">Expenses Reports</span>
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
                    <span data-i18n="nav_expenses_report">Expenses Report</span>
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

function applySidebarDesktopMode(mode, skipPersist = false) {
    const normalized = SIDEBAR_MODES.includes(mode) ? mode : 'expanded';
    _sidebarDesktopMode = normalized;
    document.documentElement.setAttribute('data-sidebar-mode', normalized);
    if (!skipPersist) {
        localStorage.setItem(SIDEBAR_MODE_KEY, normalized);
    }
    updateSidebarModeButton();
}

function updateSidebarModeButton() {
    const btn = document.getElementById('desktop-sidebar-mode-btn');
    if (!btn) return;

    let icon = 'bi-layout-sidebar-inset';
    let title = 'Sidebar: Expanded';
    if (_sidebarDesktopMode === 'collapsed') {
        icon = 'bi-layout-sidebar';
        title = 'Sidebar: Collapsed';
    } else if (_sidebarDesktopMode === 'hidden') {
        icon = 'bi-layout-sidebar-reverse';
        title = 'Sidebar: Hidden';
    }

    btn.setAttribute('title', `${title} (click to change)`);
    btn.setAttribute('aria-label', title);
    btn.innerHTML = `<i class="bi ${icon}"></i>`;
}

function toggleSidebarDesktopMode() {
    const currentIndex = SIDEBAR_MODES.indexOf(_sidebarDesktopMode);
    const nextIndex = (currentIndex + 1) % SIDEBAR_MODES.length;
    applySidebarDesktopMode(SIDEBAR_MODES[nextIndex]);
}

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

