// app.js — init, sidebar, routing, modals, toasts
let _companies = [];
let _banks = [];
let _activeRoute = "";

document.addEventListener("DOMContentLoaded", async () => {
    await loadLanguage(localStorage.getItem("lang") || "en");
    await initApp();
    window.addEventListener("hashchange", route);
    route();
});

// Loading helpers: show/hide global spinner overlay
function showLoading() {
    const el = document.querySelector(".spinner-overlay");
    if (el) el.style.display = "flex";
}
function hideLoading() {
    const el = document.querySelector(".spinner-overlay");
    if (el) el.style.display = "none";
}

window.showLoading = showLoading;
window.hideLoading = hideLoading;

async function initApp() {
    const [cRes, bRes, meRes, profileRes] = await Promise.all([
        fetch("/api/companies/"),
        fetch("/api/banks/"),
        fetch("/api/auth/me/"),
        fetch("/api/auth/profile/"),
    ]);
    const cData = await cRes.json();
    const bData = await bRes.json();
    const meData = await meRes.json();
    const pData = await profileRes.json(); // Contains avatar/bio/full_name
    _companies = cData.companies;
    _banks = bData.banks;
    // MERGE the two sources of truth into one object
    window._currentUser = {
        ...meData.user, // From /api/auth/me/ (includes email)
        ...pData.profile, // From /api/auth/profile/ (includes avatar/bio)
    };
    renderSidebar();
    renderTopbar();
}

function renderSidebar() {
    const sidebar = document.getElementById("sidebar");
    const companyItems = _companies
        .map(
            (c) => `
        <button class="nav-item" data-route="salary-${c.id}" onclick="navigate('salary-${c.id}')">
            <span class="nav-dot" style="background:${c.color_hex}"></span>
            <span>${c.display_name}</span>
        </button>`,
        )
        .join("");

    sidebar.innerHTML = `
        <div class="sidebar-brand">
            <div class="brand-icon">💰</div>
            <div class="brand-text">
            <span data-i18n="app_title">Salary &amp; Balance Tracker</span>
            </div>
        </div>
        <nav class="sidebar-nav">
            <button class="nav-item" onclick="navigate('dashboard')">
                <i class="bi bi-speedometer2"></i>
                <span data-i18n="nav_dashboard">Dashboard</span>
            </button>

            <div class="nav-section-header" onclick="toggleSection(this)" style="cursor:pointer; padding: 10px; display:flex; justify-content:space-between;">
                <span data-i18n="nav_salary">Salary</span>
                <i class="bi bi-chevron-down chevron-icon"></i>
            </div>
            <div class="nav-section-content">
                ${companyItems}
                <button class="nav-item" onclick="navigate('all-companies')">
                <i class="bi bi-building"></i>
                <span data-i18n="nav_all_companies">All Companies</span>
                </button>
            </div>

            <div style="border-top:1px solid var(--border-color); margin:10px 0;"></div>
            <button class="nav-item" onclick="navigate('balance')"><i class="bi bi-wallet2"></i>
            <span data-i18n="nav_balance">Balance</span>
            </button>
            <button class="nav-item" onclick="navigate('bank-certificates')"><i class="bi bi-file-earmark-text"></i>
            <span data-i18n="nav_bank_certificates">Bank Certificates</span>
            </button>
            <button class="nav-item" onclick="navigate('exchange-rates')"><i class="bi bi-currency-exchange"></i>
            <span data-i18n="nav_exchange_rates">Exchange Rates</span>
            </button>
            <button class="nav-item" onclick="navigate('gold-price')"><i class="bi bi-brilliance"></i>
            <span data-i18n="nav_gold_price">Gold Price</span>
            </button>
            <div style="border-top:1px solid var(--border-color); margin:10px 0;"></div>

            <div class="nav-section-header" onclick="toggleSection(this)" style="cursor:pointer; padding: 10px; display:flex; justify-content:space-between;">
                <span data-i18n="nav_expenses_reports">Expenses & Reports</span>
                <i class="bi bi-chevron-down chevron-icon"></i>
            </div>
            <div class="nav-section-content">
                <button class="nav-item" onclick="navigate('expenses')"><i class="bi bi-receipt"></i>
                <span data-i18n="nav_expenses">Expenses</span>
                </button>
                <button class="nav-item" onclick="navigate('expense-categories')"><i class="bi bi-tag"></i>
                <span data-i18n="nav_expense_categories">Categories</span>
                </button>
                <button class="nav-item" onclick="navigate('reports')"><i class="bi bi-graph-up"></i>
                <span data-i18n="nav_reports">Reports</span>
                </button>
            </div>

            <div style="border-top:1px solid var(--border-color); margin:10px 0;"></div>
            <button class="nav-item" onclick="navigate('settings-languages')"><i class="bi bi-gear"></i>
            <span data-i18n="nav_settings">Settings</span>
            </button>
        </nav>`;

    // ── User profile + logout at bottom of sidebar ──────────
    const u = window._currentUser;
    const uName = u ? u.display_name || u.full_name || u.username : "Guest";
    const uAvatar = u && u.avatar_url ? u.avatar_url : null;
    const avatarHTML = uAvatar
        ? `<img src="${uAvatar}" style="width:36px;height:36px;border-radius:50%;
                object-fit:cover;border:2px solid var(--border-color);flex-shrink:0">`
        : `<div style="width:36px;height:36px;border-radius:50%;
                background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                display:flex;align-items:center;justify-content:center;
                font-size:15px;font-weight:700;color:#fff;flex-shrink:0">
                ${uName.charAt(0).toUpperCase()}
           </div>`;
    const sidebarNav = sidebar.querySelector(".sidebar-nav");
    if (sidebarNav) {
        // Remove any existing footer first to prevent duplicates on re-render
        const old = sidebarNav.querySelector(".user-sidebar-footer");
        if (old) old.remove();
        const footer = document.createElement("div");
        footer.className = "user-sidebar-footer";
        footer.style.cssText =
            "border-top:1px solid var(--border-color);padding:10px 8px 8px;margin-top:auto";
        footer.innerHTML = `
            <div style="display:flex;align-items:center;gap:10px;padding:8px;
                        border-radius:8px;cursor:pointer;transition:background .15s"
                 onclick="window.showProfileModal && window.showProfileModal()"
                 onmouseenter="this.style.background='var(--bg-tertiary)'"
                 onmouseleave="this.style.background='transparent'"
                 title="Click to edit profile">
                ${avatarHTML}
                <div style="overflow:hidden;flex:1;min-width:0" class="nav-text">
                    <div style="font-size:13px;font-weight:600;color:var(--text-primary);
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                        ${uName}
                    </div>
                    <div style="font-size:11px;color:var(--text-muted)">
                        ${u ? u.email : ""}
                    </div>
                </div>
                <i class="bi bi-pencil-square nav-text"
                   style="color:var(--text-muted);font-size:13px;flex-shrink:0"></i>
            </div>
            <button onclick="window.doLogout && window.doLogout()"
                    style="width:100%;display:flex;align-items:center;gap:9px;
                           padding:8px 12px;border:none;background:none;
                           color:var(--accent-red,#ff4d6d);cursor:pointer;
                           border-radius:8px;font-size:13.5px;font-weight:600;
                           transition:background .15s;margin-top:2px"
                    onmouseenter="this.style.background='rgba(255,77,109,0.1)'"
                    onmouseleave="this.style.background='none'">
                <i class="bi bi-box-arrow-left" style="font-size:16px"></i>
                <span class="nav-text" data-i18n="nav_logout">Logout</span>
            </button>`;
        sidebarNav.appendChild(footer);
    }

    applyTranslations();
}

function renderTopbar() {
    const topbar = document.getElementById("topbar");
    topbar.innerHTML = `
        <button id="mobile-nav-trigger" class="btn text-light d-lg-none p-2 me-2" onclick="toggleMobileSidebar()" style="font-size: 20px; border: none; background: transparent;">
            <i class="bi bi-list"></i>
        </button>
        
        <div id="breadcrumb" style="font-weight:600;font-size:14px;color:var(--text-secondary)"></div>
        <div style="display:flex;align-items:center;gap:12px">
            <div class="dropdown">
                <button class="btn-icon dropdown-toggle" data-bs-toggle="dropdown" id="langBtn">
                    🌐 <span id="langLabel">EN</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end" id="langMenu"
                    style="background:var(--bg-secondary);border:1px solid var(--border-color)">
                </ul>
            </div>
            <button class="btn-primary-custom" id="addEntryBtn" onclick="triggerAddEntry()" style="display:none">
                <i class="bi bi-plus-lg"></i> <span data-i18n="btn_add">Add</span>
            </button>
        </div>`;
    loadLangMenu();
}

async function loadLangMenu() {
    const res = await fetch("/api/settings/");
    const data = await res.json();
    try {
        const langs = JSON.parse(data.settings.available_languages || "[]");
        const menu = document.getElementById("langMenu");
        if (!menu) return;
        menu.innerHTML = langs
            .map(
                (l) => `
            <li><a class="dropdown-item" href="#"
                style="color:var(--text-primary)"
                onclick="loadLanguage('${l.code}');document.getElementById('langLabel').textContent='${l.code.toUpperCase()}';return false">
                ${l.label}
            </a></li>`,
            )
            .join("");
        const active = data.settings.active_language || "en";
        const el = document.getElementById("langLabel");
        if (el) el.textContent = active.toUpperCase();
    } catch (e) { }
}

function navigate(route) {
    window.location.hash = route;
}
function setBreadcrumb(title, subtitle = "") {
    const bc = document.getElementById("breadcrumb");
    if (bc) {
        bc.textContent = title;
        // If you want to show the subtitle as well, you can add it here:
        // bc.innerHTML = `${title} <small class="text-muted">${subtitle}</small>`;
    }
}
window.setBreadcrumb = setBreadcrumb;

/**
 * Helper to get the HTML for a loading state
 */
function loadingHTML() {
    return `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Loading...</p>
        </div>
    `;
}

// Make sure it is globally accessible
window.loadingHTML = loadingHTML;

function route() {
    const hash = window.location.hash.replace("#", "") || "dashboard";
    _activeRoute = hash;

    // Update active nav
    document.querySelectorAll(".nav-item").forEach((el) => {
        el.classList.toggle("active", el.dataset.route === hash);
    });

    const addBtn = document.getElementById("addEntryBtn");
    const bc = document.getElementById("breadcrumb");

    if (hash === "dashboard") {
        if (addBtn) addBtn.style.display = "none";
        if (bc) bc.textContent = t("nav_dashboard", "Dashboard");
        renderDashboard();
    } else if (hash.startsWith("salary-")) {
        const id = parseInt(hash.split("-")[1]);
        const c = _companies.find((x) => x.id === id);
        if (addBtn) {
            addBtn.style.display = "inline-flex";
        }
        if (bc && c) bc.textContent = c.display_name;
        renderSalaryPage(id);
    } else if (hash === "balance") {
        if (addBtn) {
            addBtn.style.display = "inline-flex";
        }
        if (bc) bc.textContent = t("nav_balance", "Balance");
        renderBalance();
    } else if (hash === "bank-certificates") {
        if (addBtn) {
            addBtn.style.display = "inline-flex";
        }
        if (bc) bc.textContent = t("nav_bank_certificates", "Bank Certificates");
        renderBankCertificates();
    } else if (hash === "all-companies") {
        if (addBtn) {
            addBtn.style.display = "inline-flex";
        }
        if (bc) bc.textContent = t("nav_all_companies", "All Companies");
        renderAllCompanies();
    } else if (hash === "exchange-rates") {
        if (typeof setBreadcrumb === "function")
            setBreadcrumb(t("nav_exchange_rates", "Exchange Rates"), "");
        if (typeof bc !== "undefined" && bc)
            bc.textContent = t("nav_exchange_rates", "Exchange Rates");
        renderExchangeRates();
    } else if (hash === "gold-price") {
        if (typeof setBreadcrumb === "function")
            setBreadcrumb(t("nav_gold_price", "Gold Price"), "");
        if (typeof bc !== "undefined" && bc)
            bc.textContent = t("nav_gold_price", "Gold Price");
        renderGoldPrice();
    } else if (hash === "expenses") {
        setBreadcrumb("Expenses", "Track your spending");
        renderExpenses();
    } else if (hash === "expense-categories") {
        setBreadcrumb("Expense Categories", "");
        renderExpenseCategories();
    } else if (hash === "reports") {
        setBreadcrumb("Reports", "Income & Expense Analysis");
        renderReports();
    } else if (hash.startsWith("settings")) {
        if (addBtn) addBtn.style.display = "none";
        if (bc) bc.textContent = t("nav_settings", "Settings");
        renderSettings(hash);
    }
    applyTranslations();
}

function triggerAddEntry() {
    const hash = window.location.hash.replace("#", "");
    if (hash.startsWith("salary-")) {
        const id = parseInt(hash.split("-")[1]);
        showSalaryModal(null, id);
    } else if (hash === "balance") {
        showBalanceModal(null);
    } else if (hash === "bank-certificates") {
        showBankCertificateModal(null);
    } else if (hash === "all-companies") {
        showCompanyModal(null);
    }
}

// ── Modal helpers ──────────────────────────────────────────
function showModal(html) {
    let el = document.getElementById("globalModal");
    if (!el) {
        el = document.createElement("div");
        el.id = "globalModal";
        el.className = "modal fade modal-dark";
        el.setAttribute("tabindex", "-1");
        document.body.appendChild(el);
    }
    el.innerHTML = `<div class="modal-dialog modal-dialog-centered"><div class="modal-content">${html}</div></div>`;
    const m = new bootstrap.Modal(el);
    m.show();
    return m;
}

function closeModal() {
    const el = document.getElementById("globalModal");
    if (el) {
        const m = bootstrap.Modal.getInstance(el);
        if (m) m.hide();
    }
}

// ── Toast ──────────────────────────────────────────────────
function showToast(msg, type = "success") {
    const container = document.getElementById("toast-container");
    const id = "toast-" + Date.now();
    const color =
        type === "success" ? "var(--accent-green)" : "var(--accent-red)";
    container.insertAdjacentHTML(
        "beforeend",
        `
        <div id="${id}" class="toast align-items-center" role="alert" style="border-left:3px solid ${color}">
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`,
    );
    const toast = new bootstrap.Toast(document.getElementById(id), {
        delay: 3000,
    });
    toast.show();
}

function fmt(n) {
    if (n === null || n === undefined) return "-";
    return Number(n).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 6,
    });
}

function fmtpresent(n) {
    if (n === null || n === undefined) return "-";
    return Number(n).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function amtClass(n) {
    if (n > 0) return "amt-negative";
    if (n < 0) return "amt-positive";
    return "amt-zero";
}

function fmtInt(n) {
    if (n === null || n === undefined) return "-";
    return Number(n).toLocaleString("en-US");
}

/* Expose globals used by salary.js, balance.js, settings.js */

/* ── Auth: Logout, Profile Modal, Avatar Upload ─────────── */

async function doLogout() {
    try {
        await fetch("/api/auth/logout/", { method: "POST" });
    } catch (_) { }
    window.location.href = "/accounts/login/";
}

function showProfileModal() {
    const u = window._currentUser || {};
    const name = u.display_name || u.full_name || u.username || "";
    const avatar = u.avatar_url;
    const initials = name ? name.charAt(0).toUpperCase() : "?";

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title">
                <i class="bi bi-person-circle"
                   style="color:var(--accent-primary);margin-right:8px"></i>My Profile
            </h5>
            <button type="button" class="btn-close btn-close-white"
                    data-bs-dismiss="modal" onclick="closeModal()"></button>
        </div>
        <div class="modal-body">
            <div style="text-align:center;margin-bottom:22px">
                <div style="position:relative;display:inline-block">
                    ${avatar
            ? `<img src="${avatar}" id="avatarPreview"
                                style="width:90px;height:90px;border-radius:50%;
                                       object-fit:cover;border:3px solid var(--border-color)">`
            : `<div id="avatarPreview"
                                style="width:90px;height:90px;border-radius:50%;
                                       background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                                       display:inline-flex;align-items:center;justify-content:center;
                                       font-size:36px;font-weight:700;color:#fff;
                                       border:3px solid var(--border-color)">
                                ${initials}
                           </div>`
        }
                    <label for="avatarInput"
                           style="position:absolute;bottom:2px;right:2px;
                                  background:var(--accent-primary);color:#fff;
                                  width:28px;height:28px;border-radius:50%;
                                  display:flex;align-items:center;justify-content:center;
                                  cursor:pointer;font-size:13px;
                                  border:2px solid var(--bg-secondary)"
                           title="Upload photo">
                        <i class="bi bi-camera"></i>
                    </label>
                    <input type="file" id="avatarInput" accept="image/*"
                           style="display:none"
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
                           value="${u.username || ""}" disabled style="opacity:.6">
                </div>
                <div class="col-12">
                    <label class="form-label">Email</label>
                    <input type="text" class="form-control"
                           value="${u.email || ""}" disabled style="opacity:.6">
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
    const reader = new FileReader();
    reader.onload = (e) => {
        const prev = document.getElementById("avatarPreview");
        if (prev)
            prev.outerHTML = `<img id="avatarPreview" src="${e.target.result}"
                 style="width:90px;height:90px;border-radius:50%;
                        object-fit:cover;border:3px solid var(--border-color)">`;
    };
    reader.readAsDataURL(file);
    const fd = new FormData();
    fd.append("avatar", file);
    try {
        const res = await fetch("/api/auth/profile/avatar/", {
            method: "POST",
            body: fd,
        });
        const data = await res.json();
        if (res.ok) {
            if (window._currentUser) window._currentUser.avatar_url = data.avatar_url;
            showToast("Photo updated ✓", "success");
            renderSidebar();
        } else {
            showToast("Upload failed: " + (data.error || ""), "error");
        }
    } catch (e) {
        showToast("Upload error: " + e.message, "error");
    }
}

async function saveProfile() {
    const fullName = (
        document.getElementById("profileFullName")?.value || ""
    ).trim();
    try {
        const res = await fetch("/api/auth/profile/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_name: fullName }),
        });
        const data = await res.json();
        if (res.ok) {
            if (window._currentUser) {
                window._currentUser.full_name = data.profile.full_name;
                window._currentUser.display_name = data.profile.display_name;
            }
            closeModal();
            showToast("Profile saved ✓", "success");
            renderSidebar();
        } else {
            showToast("Error: " + (data.error || ""), "error");
        }
    } catch (e) {
        showToast("Error: " + e.message, "error");
    }
}

function toggleSection(element) {
    const content = element.nextElementSibling;
    const icon = element.querySelector(".chevron-icon");
    if (content.style.display === "none") {
        content.style.display = "block";
        icon.classList.replace("bi-chevron-right", "bi-chevron-down");
    } else {
        content.style.display = "none";
        icon.classList.replace("bi-chevron-down", "bi-chevron-right");
    }
}

/* ── Mobile sidebar toggle ───────────────────────────────── */
function toggleMobileSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const isOpen = sidebar.classList.contains("open");
    sidebar.classList.toggle("open", !isOpen);
    if (overlay) overlay.classList.toggle("show", !isOpen);
}

function closeMobileSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("show");
}
window.navigate = navigate;
window.showModal = showModal;
window.closeModal = closeModal;
window.showToast = showToast;
window.fmt = fmt;
window.fmtInt = fmtInt;
window.amtClass = amtClass;
window.renderSidebar = renderSidebar;
window.loadLangMenu = loadLangMenu;
window.closeMobileSidebar = closeMobileSidebar;
window.toggleMobileSidebar = toggleMobileSidebar;
window.getCompanies = () => _companies;
window.getBanks = () => _banks;
window.refreshBanks = async () => {
    const r = await fetch("/api/banks/");
    _banks = (await r.json()).banks || [];
};
window.refreshCompanies = async () => {
    const r = await fetch("/api/companies/");
    _companies = (await r.json()).companies || [];
};
