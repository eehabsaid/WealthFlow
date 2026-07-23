'use strict';

// salary.js — Employment module and salary page rendering

const MONTHS = [
    'January', 'February', 'March',     'April',
    'May',     'June',     'July',      'August',
    'September','October', 'November',  'December',
];

let _currentEmploymentCompanyId = null;

function getCurrentEmploymentCompanyId() {
    return _currentEmploymentCompanyId;
}

async function renderEmploymentPage(companyId = null) {
    const mc = document.getElementById('main-content');
    if (!mc) return;

    const companies = _companies || [];
    if (companies.length === 0) {
        mc.innerHTML = `
            <div class="page-header">
                <div><div class="page-title" data-i18n="nav_employment">Employment</div></div>
            </div>
            <div class="alert alert-info mt-3" style="border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary);">
                <i class="bi bi-info-circle me-2"></i><span data-i18n="no_employers_found">No employers found. Please configure companies in Settings.</span>
            </div>`;
        applyTranslations();
        return;
    }

    let activeId = companyId;
    if (!activeId || !companies.some(c => c.id === activeId)) {
        activeId = companies[0].id;
    }
    _currentEmploymentCompanyId = activeId;

    const initialCompany = companies.find(c => c.id === activeId) || companies[0];
    const initialActionsHtml = (initialCompany && initialCompany.is_active) ? `
        <button class="btn btn-success btn-primary-custom" onclick="generateCurrentSalary(${activeId})" data-i18n="generate_current_month">
            🔄 Generate Current Month
        </button>
        <button class="btn btn-primary-custom" onclick="showPerDiemListModal(${activeId})" data-i18n="per_diem">
            ✈️ Per Diem
        </button>` : '';

    const tabsHtml = companies.map(c => {
        const isActive = c.id === activeId;
        const colorDot = c.color_hex ? `<span class="nav-dot" style="background:${c.color_hex};display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px"></span>` : '';
        return `
            <button class="wf-tab employer-tab ${isActive ? 'active' : ''}"
                    id="tab-employer-${c.id}"
                    data-employer-id="${c.id}"
                    data-route="employment-${c.id}"
                    onclick="switchEmployerTab(${c.id})"
                    type="button"
                    role="tab"
                    aria-selected="${isActive}">
                ${colorDot}${c.display_name || c.name}
            </button>`;
    }).join('');

    mc.innerHTML = `
        <div class="page-header mb-3">
            <div>
                <div class="page-title" id="employmentPageTitle">${initialCompany ? (initialCompany.display_name || initialCompany.name) : ''}</div>
                <div class="page-subtitle" id="employmentPageSubtitle" style="font-size:13px;color:var(--text-secondary);margin-top:2px">${initialCompany ? (initialCompany.group_name || '') : ''}</div>
            </div>
            <div id="employmentHeaderActions" style="display:${(initialCompany && initialCompany.is_active) ? 'flex' : 'none'};gap:10px">
                ${initialActionsHtml}
            </div>
        </div>

        <div class="wf-tabs-shell">
            <div class="wf-tabs-row" id="employmentTabsRow" role="tablist">
                ${tabsHtml}
            </div>
        </div>

        <div id="employerTabContent" class="tab-content mt-3">
            <div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>
        </div>
    `;

    applyTranslations();

    if (typeof window.initTabsWithMoreMenu === 'function') {
        window.initTabsWithMoreMenu({
            containerId: 'employmentTabsRow',
            visibleCount: 4,
            moreLabel: typeof t === 'function' ? t('financial_advisor_tab_more', 'More') : 'More',
        });
    }

    await loadEmployerTabContent(activeId);
}

async function switchEmployerTab(companyId) {
    if (_currentEmploymentCompanyId === companyId) return;
    _currentEmploymentCompanyId = companyId;

    const newHash = `employment-${companyId}`;
    if (window.location.hash !== `#${newHash}` && window.location.hash !== `#salary-${companyId}`) {
        history.pushState(null, '', `#${newHash}`);
        if (typeof _activeRoute !== 'undefined') _activeRoute = newHash;
        localStorage.setItem('wf_last_route', newHash);
    }

    document.querySelectorAll('#employmentTabsRow button[data-employer-id]').forEach(btn => {
        const id = parseInt(btn.getAttribute('data-employer-id'));
        const isActive = id === companyId;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    await loadEmployerTabContent(companyId);
}

async function loadEmployerTabContent(companyId) {
    const container = document.getElementById('employerTabContent');
    if (!container) return;

    const company = (_companies || []).find(c => c.id === companyId);
    
    // Update main page title and subtitle above the tabs
    const titleEl = document.getElementById('employmentPageTitle');
    const subTitleEl = document.getElementById('employmentPageSubtitle');
    const actionsEl = document.getElementById('employmentHeaderActions');

    if (titleEl && company) {
        titleEl.textContent = company.display_name || company.name;
    }
    if (subTitleEl) {
        subTitleEl.textContent = company ? (company.group_name || '') : '';
    }
    if (actionsEl) {
        if (company && company.is_active) {
            actionsEl.style.display = 'flex';
            actionsEl.innerHTML = `
                <button class="btn btn-success btn-primary-custom" onclick="generateCurrentSalary(${companyId})" data-i18n="generate_current_month">
                    🔄 Generate Current Month
                </button>
                <button class="btn btn-primary-custom" onclick="showPerDiemListModal(${companyId})" data-i18n="per_diem">
                    ✈️ Per Diem
                </button>`;
            applyTranslations();
        } else {
            actionsEl.style.display = 'none';
            actionsEl.innerHTML = '';
        }
    }

    container.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const res     = await fetch(`/api/salary/?company=${companyId}`);
    const data    = await res.json();
    const entries = data.entries || [];

    const years      = [...new Set(entries.map(e => e.year))].sort();
    const activeYear = years[years.length - 1] || new Date().getFullYear();

    container.innerHTML = `
        <div class="year-pills" id="yearPills"></div>
        <div id="salaryTableArea"></div>`;

    renderYearPills(years, activeYear, companyId);
    renderSalaryTable(entries, activeYear, companyId);
    applyTranslations();
}

function renderSalaryPage(companyId) {
    return renderEmploymentPage(companyId);
}

// ── Year pills ────────────────────────────────────────────────────────────

function renderYearPills(years, activeYear, companyId) {
    const container = document.getElementById('yearPills');
    if (!container) return;
    container.innerHTML = years.map(y => `
        <button class="year-pill ${y === activeYear ? 'active' : ''}"
            onclick="switchYear(${y}, ${companyId})">${y}</button>`
    ).join('');
}

async function switchYear(year, companyId) {
    document.querySelectorAll('.year-pill').forEach(p =>
        p.classList.toggle('active', parseInt(p.textContent) === year));
    const res  = await fetch(`/api/salary/?company=${companyId}`);
    const data = await res.json();
    renderSalaryTable(data.entries, year, companyId);
}

window.renderEmploymentPage = renderEmploymentPage;
window.renderSalaryPage = renderSalaryPage;
window.switchEmployerTab = switchEmployerTab;
window.getCurrentEmploymentCompanyId = getCurrentEmploymentCompanyId;
window.showPerDiemListModal = showPerDiemListModal;
window.filterPerDiems = filterPerDiems;
window.showPerDiemFormModal = showPerDiemFormModal;
window.recalcPerDiemEgp = recalcPerDiemEgp;
window.savePerDiem = savePerDiem;
window.deletePerDiem = deletePerDiem;
