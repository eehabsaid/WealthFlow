'use strict';

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
    if (hash === 'financial-advisor') {
        return !shouldShowWelcomeOnly();
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
    if (hash === 'employment' || hash === 'salary' || hash.startsWith('employment-') || hash.startsWith('salary-')) {
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

    const candidates = ['dashboard', 'financial-advisor', 'employment', 'balance', 'bank-certificates', 'fixed-assets', 'exchange-rates', 'gold-price', 'expenses', 'expense-categories', 'reports', 'advanced-reports', 'settings-languages'];
    for (const candidate of candidates) {
        if (routeAllowed(candidate)) {
            return candidate;
        }
    }
    return 'welcome';
}

function permissionToRoute(pageKey) {
    if (pageKey === 'dashboard') return 'dashboard';
    if (pageKey === 'balance') return 'balance';
    if (pageKey === 'bank_certificates') return 'bank-certificates';
    if (pageKey === 'fixed_assets') return 'fixed-assets';
    if (pageKey === 'all_companies' || pageKey === 'salary') return 'employment';
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

function route() {
    if (!_appInitialized) {
        return;
    }

    const requested = window.location.hash.replace('#', '');
    const storedRoute = localStorage.getItem('wf_last_route') || '';
    const hash = requested || storedRoute || (shouldShowWelcomeOnly() ? 'welcome' : getFirstAllowedRoute());

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
    localStorage.setItem('wf_last_route', hash);

    // Highlight active nav item
    document.querySelectorAll('.nav-item').forEach(el => {
        const routeKey = el.dataset.route;
        const isActive = routeKey === hash ||
            ((hash.startsWith('employment') || hash.startsWith('salary')) && routeKey === 'employment');
        el.classList.toggle('active', isActive);
    });

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

    } else if (hash === 'employment' || hash === 'salary' || hash.startsWith('employment-') || hash.startsWith('salary-')) {
        if (addBtn) addBtn.style.display = 'inline-flex';
        if (bc) { bc.setAttribute('data-i18n', 'nav_employment'); bc.textContent = ''; }
        let cId = null;
        if (hash.startsWith('employment-')) {
            cId = parseInt(hash.replace('employment-', ''));
        } else if (hash.startsWith('salary-')) {
            cId = parseInt(hash.replace('salary-', ''));
        }
        renderEmploymentPage(cId);

    } else if (hash.startsWith('settings')) {
        if (addBtn) addBtn.style.display = 'none';
        if (bc) { bc.setAttribute('data-i18n', 'nav_settings'); bc.textContent = ''; }
        renderSettings(hash);
    }

    applyTranslations();
}

window.route = route;

