// settings.js — settings page (languages, companies, banks)
async function renderSettings(route) {
  const mc = document.getElementById("main-content");
  const activeTab = route.includes("companies")
    ? "companies"
    : route.includes("banks")
      ? "banks"
      : route.includes("currency")
        ? "currency"
        : route.includes("users")
          ? "users"
          : route.includes("translations")
            ? "translations"
            : "languages";

  mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_settings">Settings</div></div>
        </div>
        <div style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px">
            <button class="settings-tab ${activeTab === "languages" ? "active" : ""}" onclick="navigate('settings-languages')" data-i18n="settings_languages">Languages</button>
            <button class="settings-tab ${activeTab === "companies" ? "active" : ""}" onclick="navigate('settings-companies')" data-i18n="settings_companies">Companies</button>
            <button class="settings-tab ${activeTab === "banks" ? "active" : ""}" onclick="navigate('settings-banks')" data-i18n="settings_banks">Banks</button>
            <button class="settings-tab ${activeTab === "currency" ? "active" : ""}" onclick="navigate('settings-currency')">Currency</button>
            <button class="settings-tab ${activeTab === "users" ? "active" : ""}" onclick="navigate('settings-users')">Users</button>
            <button class="settings-tab ${activeTab === "translations" ? "active" : ""}" onclick="navigate('settings-translations')">Translations</button>
        </div>
        <div id="settingsContent"></div>`;
  applyTranslations();

  if (activeTab === "languages") renderLanguageSettings();
  else if (activeTab === "companies") renderCompanySettings();
  else if (activeTab === "currency") renderCurrencySettings();
  else if (activeTab === "users") renderUserSettings();
  else if (activeTab === "translations") renderTranslationSettings();
  else renderBankSettings();
}

// ── Language Settings ──────────────────────────────────────
async function renderLanguageSettings() {
  const res = await fetch("/api/settings/");
  const data = await res.json();
  const activeLang = data.settings.active_language || "en";
  let langs = [];
  try {
    langs = JSON.parse(data.settings.available_languages || "[]");
  } catch (e) {}

  // Inside renderLanguageSettings
  const rows = langs
    .map(
      (l, i) => `
    <tr style="background: var(--bg-secondary);">
        <td style="padding: 12px; border-bottom: 1px solid var(--border-color);"><code style="color:var(--accent-yellow)">${l.code}</code></td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border-color);">${l.label}</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border-color);">${l.rtl ? "✓" : "—"}</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border-color);">${
          l.code === activeLang
            ? '<span style="color:var(--accent-green);font-weight:700">● Active</span>'
            : `<button class="btn-icon" onclick="setActiveLang('${l.code}')">Set Active</button>`
        }</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border-color);">
            <button class="btn-icon del" onclick="deleteLang(${i})"><i class="bi bi-trash"></i></button>
        </td>
    </tr>`,
    )
    .join("");

  // Update the table container and table tag
  document.getElementById("settingsContent").innerHTML = `
    ... (header div)
    <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; overflow:hidden">
        <table class="data-table" style="width: 100%; border-collapse: collapse; background: var(--bg-secondary);">
            <thead>
                <tr>
                    <th style="padding: 12px; text-align: left;" data-i18n="language_code">Code</th>
                    <th style="padding: 12px; text-align: left;" data-i18n="language_label">Label</th>
                    <th style="padding: 12px; text-align: left;" data-i18n="language_rtl">RTL</th>
                    <th style="padding: 12px; text-align: left;" data-i18n="active">Active</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    </div>`;
  applyTranslations();
}

async function setActiveLang(code) {
  await loadLanguage(code);
  document.getElementById("langLabel").textContent = code.toUpperCase();
  renderLanguageSettings();
}

async function deleteLang(idx) {
  if (!confirm("Remove this language?")) return;
  const res = await fetch("/api/settings/");
  const data = await res.json();
  let langs = JSON.parse(data.settings.available_languages || "[]");
  langs.splice(idx, 1);
  await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      key: "available_languages",
      value: JSON.stringify(langs),
    }),
  });
  showToast("Language removed");
  renderLanguageSettings();
}

function showAddLangModal() {
  const html = `
        <div class="modal-header">
            <h5 class="modal-title">Add Language</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-4">
                    <label>Code (e.g. fr)</label>
                    <input type="text" class="form-control" id="lCode" placeholder="fr" maxlength="5">
                </div>
                <div class="col-5">
                    <label>Label (e.g. Français)</label>
                    <input type="text" class="form-control" id="lLabel" placeholder="Français">
                </div>
                <div class="col-3">
                    <label>RTL?</label>
                    <select class="form-select" id="lRTL"><option value="false">No</option><option value="true">Yes</option></select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
            <button class="btn-primary-custom" onclick="saveNewLang()">Add</button>
        </div>`;
  showModal(html);
}

async function saveNewLang() {
  const code = document.getElementById("lCode").value.trim().toLowerCase();
  const label = document.getElementById("lLabel").value.trim();
  const rtl = document.getElementById("lRTL").value === "true";
  if (!code || !label) {
    showToast("Code and label required", "error");
    return;
  }
  const res = await fetch("/api/settings/");
  const data = await res.json();
  let langs = [];
  try {
    langs = JSON.parse(data.settings.available_languages || "[]");
  } catch (e) {}
  if (!langs.find((l) => l.code === code)) langs.push({ code, label, rtl });
  await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      key: "available_languages",
      value: JSON.stringify(langs),
    }),
  });
  closeModal();
  showToast(`Language "${label}" added`);
  renderLanguageSettings();
  loadLangMenu();
}

async function renderCurrencySettings() {
  const res = await fetch("/api/currencies/");
  const data = await res.json();
  const currencies = data.currencies || [];

  const rows = currencies
    .map(
      (c) => `
        <tr>
            <td style="font-size:20px">${c.flag}</td>
            <td><code style="color:var(--accent-primary);font-weight:700">${c.code}</code></td>
            <td>${c.symbol || "—"}</td>
            <td>${c.name}</td>
            <td>
                <button class="btn-icon" onclick="showCurrencyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCurrency(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)">Currency Settings</div>
            <button class="btn-primary-custom" onclick="showCurrencyModal(null)"><i class="bi bi-plus-lg"></i> Add Currency</button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                    <th>Flag</th>
                    <th>Code</th>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th></th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        <div style="margin-top:14px;font-size:13px;color:var(--text-secondary)">
            Manage currency codes, symbols, and flags that appear in the Balance page.
        </div>`;
}

async function showCurrencyModal(currencyId) {
  let c = null;
  if (currencyId) {
    const res = await fetch(`/api/currencies/${currencyId}/`);
    c = await res.json();
  }
  const html = `
        <div class="modal-header">
            <h5 class="modal-title">${c ? "Edit" : "Add"} Currency</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-4"><label>Code</label><input class="form-control" id="curCode" value="${c ? c.code : ""}" placeholder="USD"></div>
                <div class="col-4"><label>Symbol</label><input class="form-control" id="curSymbol" value="${c ? c.symbol : ""}" placeholder="$"></div>
                <div class="col-4"><label>Flag</label><input class="form-control" id="curFlag" value="${c ? c.flag : "💱"}" placeholder="🇺🇸" maxlength="5"></div>
                <div class="col-12"><label>Name</label><input class="form-control" id="curName" value="${c ? c.name : ""}" placeholder="US Dollar"></div>
                <div class="col-4"><label>Order</label><input type="number" class="form-control" id="curOrder" value="${c ? c.order : 0}"></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCurrency(${currencyId})">Save</button>
        </div>`;
  showModal(html);
}

async function saveCurrency(currencyId) {
  const body = {
    code: document.getElementById("curCode").value.toUpperCase(),
    symbol: document.getElementById("curSymbol").value,
    flag: document.getElementById("curFlag").value,
    name: document.getElementById("curName").value,
    order: parseInt(document.getElementById("curOrder").value) || 0,
  };

  if (!body.code || !body.name) {
    showToast("Code and Name are required", "error");
    return;
  }

  const url = currencyId
    ? `/api/currencies/${currencyId}/`
    : "/api/currencies/";
  const method = currencyId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Currency saved ✓");
    renderCurrencySettings();
  } else showToast("Error", "error");
}

async function deleteCurrency(currencyId) {
  if (!confirm("Delete this currency?")) return;
  const res = await fetch(`/api/currencies/${currencyId}/`, {
    method: "DELETE",
  });
  if (res.ok) {
    showToast("Deleted");
    renderCurrencySettings();
  } else {
    showToast("Error deleting currency", "error");
  }
}

// ── Company Settings ───────────────────────────────────────
async function renderCompanySettings() {
  const res = await fetch("/api/companies/");
  const data = await res.json();
  const rows = data.companies
    .map(
      (c) => `
        <tr>
            <td><span style="background:${c.color_hex};width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:8px"></span>${c.name}</td>
            <td>${c.display_name}</td>
            <td><span class="group-badge">${c.group_name || "—"}</span></td>
            <td><input type="color" value="${c.color_hex}" onchange="updateCompanyColor(${c.id},this.value)" style="background:none;border:none;width:32px;height:32px;cursor:pointer"></td>
            <td>${c.order}</td>
            <td><span style="color:${c.is_active ? "var(--accent-green)" : "var(--accent-red)"}">${c.is_active ? "Active" : "Inactive"}</span></td>
            <td>
                <button class="btn-icon" onclick="showCompanyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCompany(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_companies">Companies</div>
            <button class="btn-primary-custom" onclick="showCompanyModal(null)"><i class="bi bi-plus-lg"></i> Add Company</button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                    <th>Name</th><th>Display Name</th><th data-i18n="group_name">Group</th>
                    <th data-i18n="color">Color</th><th data-i18n="order">Order</th>
                    <th data-i18n="active">Active</th><th></th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
  applyTranslations();
}

async function updateCompanyColor(id, color) {
  await fetch(`/api/companies/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ color_hex: color }),
  });
  _companies = _companies.map((c) =>
    c.id === id ? { ...c, color_hex: color } : c,
  );
  renderSidebar();
}

async function showCompanyModal(companyId) {
  let c = null;
  if (companyId) {
    const res = await fetch(`/api/companies/${companyId}/`);
    c = await res.json();
  }
  const html = `
        <div class="modal-header">
            <h5 class="modal-title">${c ? "Edit" : "Add"} Company</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6"><label>Name</label><input class="form-control" id="cName" value="${c ? c.name : ""}"></div>
                <div class="col-6"><label>Display Name</label><input class="form-control" id="cDisplay" value="${c ? c.display_name : ""}"></div>
                <div class="col-6"><label>Group Name</label><input class="form-control" id="cGroup" value="${c ? c.group_name : ""}"></div>
                <div class="col-3"><label>Color</label><input type="color" class="form-control" id="cColor" value="${c ? c.color_hex : "#0d6efd"}"></div>
                <div class="col-3"><label>Order</label><input type="number" class="form-control" id="cOrder" value="${c ? c.order : 0}"></div>
                <div class="col-12"><label>Active</label>
                    <select class="form-select" id="cActive">
                        <option value="true" ${!c || c.is_active ? "selected" : ""}>Active</option>
                        <option value="false" ${c && !c.is_active ? "selected" : ""}>Inactive</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCompany(${companyId})">Save</button>
        </div>`;
  showModal(html);
}

async function saveCompany(companyId) {
  const body = {
    name: document.getElementById("cName").value,
    display_name: document.getElementById("cDisplay").value,
    group_name: document.getElementById("cGroup").value,
    color_hex: document.getElementById("cColor").value,
    order: parseInt(document.getElementById("cOrder").value) || 0,
    is_active: document.getElementById("cActive").value === "true",
  };
  const url = companyId ? `/api/companies/${companyId}/` : "/api/companies/";
  const method = companyId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Company saved ✓");
    const cRes = await fetch("/api/companies/");
    _companies = (await cRes.json()).companies;
    renderSidebar();
    renderCompanySettings();
  } else showToast("Error", "error");
}

async function deleteCompany(id) {
  if (!confirm("Delete company? This will also delete all salary entries!"))
    return;
  await fetch(`/api/companies/${id}/`, { method: "DELETE" });
  showToast("Deleted");
  const cRes = await fetch("/api/companies/");
  _companies = (await cRes.json()).companies;
  renderSidebar();
  renderCompanySettings();
}

// ── Bank Settings ──────────────────────────────────────────
async function renderBankSettings() {
  const res = await fetch("/api/banks/");
  const data = await res.json();
  _banks = data.banks;
  const rows = data.banks
    .map(
      (b) => `
        <tr>
            <td>${b.name}</td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.account_number || "—"}</code></td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.swift_code || "—"}</code></td>
            <td><span style="color:${b.is_active ? "var(--accent-green)" : "var(--accent-red)"}">${b.is_active ? "Active" : "Inactive"}</span></td>
            <td>
                <button class="btn-icon" onclick="showBankModal(${b.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBank(${b.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_banks">Banks</div>
            <button class="btn-primary-custom" onclick="showBankModal(null)"><i class="bi bi-plus-lg"></i> Add Bank</button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                    <th>Name</th><th>Account</th><th>Swift</th><th>Active</th><th></th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
  applyTranslations();
}

async function showBankModal(bankId) {
  let b = null;
  if (bankId) {
    const r = await fetch("/api/banks/");
    b = (await r.json()).banks.find((x) => x.id === bankId);
  }
  const html = `
        <div class="modal-header">
            <h5 class="modal-title">${b ? "Edit" : "Add"} Bank</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12"><label>Bank Name</label><input class="form-control" id="bnName" value="${b ? b.name : ""}"></div>
                <div class="col-6"><label>Account Number</label><input class="form-control" id="bnAcct" value="${b ? b.account_number : ""}"></div>
                <div class="col-6"><label>Card ID</label><input class="form-control" id="bnCard" value="${b ? b.card_id : ""}"></div>
                <div class="col-4"><label>Swift Code</label><input class="form-control" id="bnSwift" value="${b ? b.swift_code : ""}"></div>
                <div class="col-4"><label>Customer ID</label><input class="form-control" id="bnCustId" value="${b ? b.customer_id : ""}"></div>
                <div class="col-4"><label>Customer Name</label><input class="form-control" id="bnCustName" value="${b ? b.customer_name : ""}"></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBank(${bankId})">Save</button>
        </div>`;
  showModal(html);
}

async function saveBank(bankId) {
  const body = {
    name: document.getElementById("bnName").value,
    account_number: document.getElementById("bnAcct").value,
    card_id: document.getElementById("bnCard").value,
    swift_code: document.getElementById("bnSwift").value,
    customer_id: document.getElementById("bnCustId").value,
    customer_name: document.getElementById("bnCustName").value,
  };
  const url = bankId ? `/api/banks/${bankId}/` : "/api/banks/";
  const method = bankId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Bank saved ✓");
    renderBankSettings();
  } else showToast("Error", "error");
}

async function deleteBank(id) {
  if (!confirm("Delete this bank?")) return;
  await fetch(`/api/banks/${id}/`, { method: "DELETE" });
  showToast("Deleted");
  renderBankSettings();
}

// ── User Management (In-app) ─────────────────────────────────
async function renderUserSettings() {
  const mc = document.getElementById("settingsContent");
  mc.innerHTML = `<div style="font-weight:600;color:var(--text-secondary)">Users</div>`;

  // Check current user permissions
  const meRes = await fetch("/api/auth/me/");
  const me = await meRes.json();
  const allowedPages = me.allowed_pages || [];
  const canManage =
    (me.user && me.user.is_staff) || allowedPages.includes("user_management");
  if (!canManage) {
    mc.innerHTML = `<div class="p-4">You do not have permission to manage users.</div>`;
    return;
  }

  // use server-side pagination and search
  const page = 1;
  const pageSize = 10;
  await loadUsers({ page, pageSize, q: "" });
}

async function loadUsers({ page = 1, pageSize = 10, q = "" } = {}) {
  const mc = document.getElementById("settingsContent");
  mc.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="font-weight:600;color:var(--text-secondary)">Users</div>
            <div style="display:flex;gap:8px">
                <input id="userSearch" class="form-control" placeholder="Search username or email" style="width:260px" value="${q}">
                <button class="btn-primary-custom" onclick="handleUserSearch()">Search</button>
                <button class="btn-primary-custom" onclick="showUserModal(null)"><i class="bi bi-plus-lg"></i> Add User</button>
            </div>
        </div>
        <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
            <div>
                <button class="btn-secondary-custom" onclick="toggleSelectAll()">Toggle Select</button>
            </div>
            <div>
                <select id="bulkActionSelect" class="form-select" style="width:220px">
                    <option value="">Bulk actions</option>
                    <option value="activate">Activate selected</option>
                    <option value="deactivate">Deactivate selected</option>
                    <option value="delete">Delete selected</option>
                    <option value="set_staff_true">Set staff</option>
                    <option value="set_staff_false">Unset staff</option>
                </select>
            </div>
            <div><button class="btn-primary-custom" onclick="applyBulkAction()">Apply</button></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead>
                    <tr><th></th><th>Username</th><th>Email</th><th>Active</th><th>Roles</th><th></th></tr>
                </thead>
                <tbody id="usersTableBody"></tbody>
            </table>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
            <div id="usersPager"></div>
            <div><select id="usersPageSize" class="form-select" style="width:80px"><option>5</option><option selected>10</option><option>25</option><option>50</option></select></div>
        </div>`;

  document.getElementById("usersPageSize").value = pageSize;

  showLoading();
  let data = {};
  try {
    const resp = await fetch(
      `/api/users/?page=${page}&page_size=${pageSize}&q=${encodeURIComponent(q)}`,
    );
    if (!resp.ok) {
      document.getElementById("settingsContent").innerHTML =
        `<div class="p-4">Unable to load users (admin access required).</div>`;
      hideLoading();
      return;
    }
    data = await resp.json();
  } catch (e) {
    document.getElementById("settingsContent").innerHTML =
      `<div class="p-4">Network error loading users.</div>`;
    hideLoading();
    return;
  }
  hideLoading();
  const tbody = document.getElementById("usersTableBody");
  tbody.innerHTML = (data.users || [])
    .map(
      (u) => `
        <tr>
            <td><input type="checkbox" class="user-select" data-id="${u.id}"></td>
            <td>${u.username}</td>
            <td>${u.email || "—"}</td>
            <td>${u.is_active ? "Active" : "Inactive"}</td>
            <td>${u.is_staff ? "Staff" : ""} ${u.is_superuser ? "Super" : ""}</td>
            <td>
                <button class="btn-icon" onclick="showUserModal(${u.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon" onclick="showPermissionsModal(${u.id})"><i class="bi bi-shield-lock"></i></button>
                <button class="btn-icon del" onclick="deleteUser(${u.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
    )
    .join("");

  // pager (prev / next)
  const pager = document.getElementById("usersPager");
  const total = data.total || 0;
  const numPages = data.num_pages || 1;
  const cur = data.page || 1;
  let pagerHtml = "";
  if (numPages > 1) {
    const prevDisabled = cur <= 1 ? "disabled" : "";
    const nextDisabled = cur >= numPages ? "disabled" : "";
    pagerHtml += `<button class="btn-secondary-custom" ${prevDisabled} onclick="loadUsers({page:${cur - 1},pageSize:document.getElementById('usersPageSize').value,q:document.getElementById('userSearch').value})">Prev</button>`;
    pagerHtml += `<span style="margin:0 12px">Page <strong>${cur}</strong> of ${numPages}</span>`;
    pagerHtml += `<button class="btn-secondary-custom" ${nextDisabled} onclick="loadUsers({page:${cur + 1},pageSize:document.getElementById('usersPageSize').value,q:document.getElementById('userSearch').value})">Next</button>`;
  }
  pager.innerHTML = `${pagerHtml} <span style="margin-left:8px">Total: ${total}</span>`;

  // page size change
  document.getElementById("usersPageSize").onchange = function () {
    loadUsers({
      page: 1,
      pageSize: parseInt(this.value),
      q: document.getElementById("userSearch").value,
    });
  };
}

function handleUserSearch() {
  const q = document.getElementById("userSearch").value;
  loadUsers({
    page: 1,
    pageSize: document.getElementById("usersPageSize").value,
    q,
  });
}

function toggleSelectAll() {
  const boxes = Array.from(document.querySelectorAll(".user-select"));
  if (!boxes.length) return;
  const some = boxes.some((b) => !b.checked);
  boxes.forEach((b) => (b.checked = some));
}

function getSelectedUserIds() {
  return Array.from(document.querySelectorAll(".user-select:checked")).map(
    (cb) => parseInt(cb.dataset.id),
  );
}

async function applyBulkAction() {
  const action = document.getElementById("bulkActionSelect").value;
  const ids = getSelectedUserIds();
  if (!action) {
    showToast("Choose an action", "error");
    return;
  }
  if (!ids.length) {
    showToast("No users selected", "error");
    return;
  }
  if (action === "delete") {
    if (!confirm(`Delete ${ids.length} selected users? This cannot be undone.`))
      return;
  }
  let payload = { action, ids };
  if (action.startsWith("set_staff")) payload.value = action.endsWith("true");
  showLoading();
  try {
    const res = await fetch("/api/users/bulk/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const d = await res.json();
      showToast(`${d.changed || 0} users updated`);
      loadUsers({
        page: 1,
        pageSize: document.getElementById("usersPageSize").value,
        q: document.getElementById("userSearch").value,
      });
    } else {
      const e = await res.json().catch(() => ({}));
      showToast(e.error || "Bulk action failed", "error");
    }
  } catch (err) {
    showToast("Network error", "error");
  } finally {
    hideLoading();
  }
}

function showUserModal(userId) {
  (async () => {
    let u = null;
    if (userId) {
      const r = await fetch(`/api/users/${userId}/`);
      const d = await r.json();
      u = d.user;
    }
    const html = `
            <div class="modal-header">
                <h5 class="modal-title">${u ? "Edit" : "Add"} User</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-12"><label>Username</label><input class="form-control" id="uName" value="${u ? u.username : ""}" ${u ? "disabled" : ""}></div>
                    <div class="col-12"><label>Email</label><input class="form-control" id="uEmail" value="${u ? u.email : ""}"></div>
                    <div class="col-12"><label>Password ${u ? "(leave blank to keep)" : ""}</label><input type="password" class="form-control" id="uPassword"></div>
                    <div class="col-6"><label>Active</label><select class="form-select" id="uActive"><option value="true" ${!u || u.is_active ? "selected" : ""}>Active</option><option value="false" ${u && !u.is_active ? "selected" : ""}>Inactive</option></select></div>
                    <div class="col-6"><label>Staff</label><select class="form-select" id="uStaff"><option value="false" ${!u || !u.is_staff ? "selected" : ""}>No</option><option value="true" ${u && u.is_staff ? "selected" : ""}>Yes</option></select></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
                <button class="btn-primary-custom" onclick="saveUser(${userId})">Save</button>
            </div>`;
    showModal(html);
  })();
}

async function saveUser(userId) {
  const username = document.getElementById("uName")
    ? document.getElementById("uName").value.trim()
    : "";
  const email = document.getElementById("uEmail").value.trim();
  const password = document.getElementById("uPassword").value;
  const is_active = document.getElementById("uActive").value === "true";
  const is_staff = document.getElementById("uStaff").value === "true";

  if (!userId && !username) {
    showToast("Username required", "error");
    return;
  }
  if (!email) {
    showToast("Email required", "error");
    return;
  }

  const body = { username, email, is_active, is_staff };
  if (password) body.password = password;

  const url = userId ? `/api/users/${userId}/` : "/api/users/";
  const method = userId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("User saved ✓");
    renderUserSettings();
  } else {
    const err = await res.json().catch(() => ({}));
    showToast(err.error || "Error saving user", "error");
  }
}

async function deleteUser(id) {
  if (!confirm("Delete user? This cannot be undone.")) return;
  const res = await fetch(`/api/users/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Deleted");
    renderUserSettings();
  } else showToast("Error deleting user", "error");
}

async function showPermissionsModal(userId) {
  const r = await fetch(`/api/users/${userId}/permissions/`);
  if (!r.ok) {
    showToast("Unable to load permissions", "error");
    return;
  }
  const d = await r.json();
  const perms = d.permissions || [];
  const pages = d.available_pages || [];
  const rows = perms
    .map(
      (p) =>
        `<tr><td>${p.username}</td><td>${p.page}</td><td><button class=\"btn-icon del\" onclick=\"deletePermission(${p.id});\"><i class=\"bi bi-trash\"></i></button></td></tr>`,
    )
    .join("");
  const optHtml = pages
    .map((p) => `<option value=\"${p[0]}\">${p[1]}</option>`)
    .join("");
  const html = `
        <div class="modal-header"><h5 class="modal-title">Manage Permissions</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
        <div class="modal-body">
            <div style="margin-bottom:10px"><strong>Existing Permissions</strong></div>
            <div style="max-height:240px;overflow:auto"><table class="data-table"><thead><tr><th>User</th><th>Page</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
            <hr>
            <div class="row g-3"><div class="col-8"><select id="permPage" class="form-select">${optHtml}</select></div>
            <div class="col-4"><button class="btn-primary-custom" onclick="addPermission(${userId})">Add</button></div></div>
        </div>
        <div class="modal-footer"><button class="btn-secondary-custom" data-bs-dismiss="modal">Close</button></div>`;
  showModal(html);
}

async function addPermission(userId) {
  const page = document.getElementById("permPage").value;
  const res = await fetch(`/api/users/${userId}/permissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page }),
  });
  if (res.ok) {
    showToast("Permission added");
    showPermissionsModal(userId);
  } else {
    showToast("Error adding permission", "error");
  }
}

async function deletePermission(permId) {
  if (!confirm("Remove this permission?")) return;
  const res = await fetch(`/api/users/permissions/${permId}/`, {
    method: "DELETE",
  });
  if (res.ok) {
    showToast("Removed");
    closeModal(); /* reopen? let user reopen */
  } else showToast("Error removing permission", "error");
}

async function renderTranslationSettings() {
  const res = await fetch("/api/translations/");
  const data = await res.json();

  const en = data.en || {};
  const ar = data.ar || {};

  // Get ordered keys from English as the master list, add others, then filter/sort
  const enKeys = Object.keys(en);
  const allKeys = [...new Set([...enKeys, ...Object.keys(ar)])];

  const keys = allKeys
    .filter((k) => !k.startsWith("__"))
    .sort((a, b) => {
      const indexA = enKeys.indexOf(a);
      const indexB = enKeys.indexOf(b);

      // If both exist in EN, respect EN order
      if (indexA !== -1 && indexB !== -1) return indexA - indexB;
      // If only A is in EN, A comes first
      if (indexA !== -1) return -1;
      // If only B is in EN, B comes first
      if (indexB !== -1) return 1;
      // If neither is in EN, fallback to alphabetical
      return a.localeCompare(b);
    });

  const rows = keys
    .map(
      (key) => `
        <tr>
            <td>
                <code>${key}</code>
            </td>
            <td>
                <input
                    type="text"
                    class="form-control"
                    id="en_${key}"
                    value="${typeof en[key] === "string" ? en[key].replace(/"/g, "&quot;") : JSON.stringify(en[key] || "")}"
                >
            </td>
            <td>
                <input
                    type="text"
                    class="form-control"
                    id="ar_${key}"
                    value="${typeof ar[key] === "string" ? ar[key].replace(/"/g, "&quot;") : JSON.stringify(ar[key] || "")}"
                >
            </td>
        </tr>
    `,
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)">
                Translation Manager
            </div>
            <div>
                <button class="btn-primary-custom" onclick="saveTranslations()">
                    Save
                </button>
                <button class="btn-primary-custom" onclick="findMissingTranslations()">
                    Scan Missing Keys
                </button>
            </div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Key</th>
                        <th>English</th>
                        <th>Arabic</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}
async function saveTranslations() {
  const res = await fetch("/api/translations/");
  const data = await res.json();

  const en = {};
  const ar = {};

  const keys = [
    ...new Set([...Object.keys(data.en || {}), ...Object.keys(data.ar || {})]),
  ];

  keys.forEach((key) => {
    en[key] = document.getElementById(`en_${key}`)?.value || "";
    ar[key] = document.getElementById(`ar_${key}`)?.value || "";
  });

  await fetch("/api/translations/save/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      en,
      ar,
    }),
  });

  //alert('Saved');
  showToast("Translations saved ✓");
  renderTranslationSettings();
}
async function findMissingTranslations() {
  const res = await fetch("/api/translations/");
  const data = await res.json();

  const en = data.en || {};
  const ar = data.ar || {};

  const missingInAr = [];
  const missingInEn = [];

  Object.keys(en).forEach((k) => {
    if (!(k in ar)) missingInAr.push(k);
  });

  Object.keys(ar).forEach((k) => {
    if (!(k in en)) missingInEn.push(k);
  });

  alert(
    `Missing in Arabic: ${missingInAr.length}\n` +
      `Missing in English: ${missingInEn.length}`,
  );

  console.log("Missing in Arabic:", missingInAr);
  console.log("Missing in English:", missingInEn);
}
