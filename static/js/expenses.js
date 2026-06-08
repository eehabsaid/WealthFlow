/* ============================================================
   expenses.js — Expense Entries + Categories + Dashboard KPIs
   ============================================================ */
'use strict';

const MONTHS_NAMES = ['January','February','March','April','May','June',
                      'July','August','September','October','November','December'];
const PAYMENT_METHODS = ['Cash','Card','Bank Transfer','Other'];

/* ╔══════════════════════════════════════════════════════════╗
   ║  EXPENSE ENTRIES PAGE                                    ║
   ╚══════════════════════════════════════════════════════════╝ */
async function renderExpenses() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = loadingHTML ? loadingHTML() : '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const today = new Date();
  const [entRes, catRes, curRes] = await Promise.all([
    fetch(`/api/expenses/?year=${today.getFullYear()}&month=${today.getMonth()+1}`),
    fetch('/api/expense-categories/'),
    fetch('/api/currencies/'),
  ]);
  const entData = await entRes.json();
  const catData = await catRes.json();
  const curData = await curRes.json();

  const entries    = entData.entries    || [];
  const categories = catData.categories || [];
  const currencies = curData.currencies || [];

  window._expCategories = categories;
  window._expCurrencies = currencies;

  // KPI cards
  const totalExp  = entries.reduce((s,e) => s + e.amount, 0);
  const avgDaily  = totalExp / today.getDate();
  const topCat    = getTopCategory(entries);

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">💸 Expenses</div>
        <div class="page-subtitle">Track your daily spending</div>
      </div>
      <button class="btn-primary-custom" onclick="showExpenseModal(null)">
        <i class="bi bi-plus-lg"></i> Add Expense
      </button>
    </div>

    <!-- KPIs -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-red);--kpi-bg:var(--accent-red-bg)">
          <div class="kpi-icon"><i class="bi bi-wallet2"></i></div>
          <div class="kpi-label">This Month</div>
          <div class="kpi-value">${fmt(totalExp)}</div>
          <div class="kpi-sub">EGP total</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-yellow);--kpi-bg:var(--accent-yellow-bg)">
          <div class="kpi-icon"><i class="bi bi-calendar-day"></i></div>
          <div class="kpi-label">Daily Average</div>
          <div class="kpi-value">${fmt(avgDaily)}</div>
          <div class="kpi-sub">EGP / day</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-primary);--kpi-bg:var(--accent-blue-dim)">
          <div class="kpi-icon"><i class="bi bi-tag"></i></div>
          <div class="kpi-label">Top Category</div>
          <div class="kpi-value" style="font-size:16px">${topCat.icon} ${topCat.name}</div>
          <div class="kpi-sub">${fmt(topCat.total)} EGP</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-green);--kpi-bg:var(--accent-green-bg)">
          <div class="kpi-icon"><i class="bi bi-list-check"></i></div>
          <div class="kpi-label">Entries</div>
          <div class="kpi-value">${entries.length}</div>
          <div class="kpi-sub">this month</div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="expense-filters mb-3">
      <select id="fYear" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        ${yearOptions(today.getFullYear())}
      </select>
      <select id="fMonth" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        <option value="">All Months</option>
        ${MONTHS_NAMES.map((m,i)=>`<option value="${i+1}" ${i+1===today.getMonth()+1?'selected':''}>${m}</option>`).join('')}
      </select>
      <select id="fCategory" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        <option value="">All Categories</option>
        ${categories.map(c=>`<option value="${c.id}">${c.icon} ${c.name}</option>`).join('')}
      </select>
      <div style="position:relative;flex:1;min-width:180px">
        <i class="bi bi-search" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text-muted)"></i>
        <input type="text" id="fSearch" class="form-control form-control-sm"
               placeholder="Search..." style="padding-left:32px"
               oninput="applyExpenseFilters()">
      </div>
      <button class="btn-secondary-custom" onclick="exportExpenses()" style="padding:5px 12px;font-size:12px">
        <i class="bi bi-download"></i> Export
      </button>
    </div>

    <!-- Table -->
    <div class="table-container" id="expenseTableWrap">
      ${renderExpenseTableHTML(entries)}
    </div>`;
}

function renderExpenseTableHTML(entries) {
  if (!entries.length) {
    return `<div class="empty-state">
      <div class="empty-icon">💸</div>
      <div class="empty-title">No expenses found.</div>
      <div class="empty-sub" style="margin-top:12px">
        <button class="btn-primary-custom" onclick="showExpenseModal(null)">
          <i class="bi bi-plus-lg"></i> Add your first expense
        </button>
      </div></div>`;
  }
  const rows = entries.map(e => `
    <tr>
      <td>${e.date}</td>
      <td><span style="background:${e.category_color}22;color:${e.category_color};
                       padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700">
        ${e.category_icon} ${e.category_name || '—'}
      </span></td>
      <td style="color:var(--text-muted);font-size:12px">${e.subcategory_name || '—'}</td>
      <td>${e.description || '—'}</td>
      <td><span style="font-size:11px;color:var(--text-muted)">${e.payment_method || '—'}</span></td>
      <td class="text-end num-col amt-negative">${fmt(e.amount)}</td>
      <td style="white-space:nowrap">
        <button class="btn-icon edit" onclick="showExpenseModal(${e.id})" title="Edit">
          <i class="bi bi-pencil"></i></button>
        <button class="btn-icon del" onclick="deleteExpense(${e.id})" title="Delete">
          <i class="bi bi-trash"></i></button>
      </td>
    </tr>`).join('');

  const total = entries.reduce((s,e) => s+e.amount, 0);
  return `<table class="data-table">
    <thead><tr>
      <th>Date</th><th>Category</th><th>Subcategory</th>
      <th>Description</th><th>Method</th>
      <th class="text-end">Amount (EGP)</th><th>Actions</th>
    </tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr class="total-row">
      <td colspan="5">Total</td>
      <td class="text-end num-col">${fmt(total)}</td>
      <td></td>
    </tr></tfoot>
  </table>`;
}

async function applyExpenseFilters() {
  const year  = document.getElementById('fYear')?.value || '';
  const month = document.getElementById('fMonth')?.value || '';
  const catId = document.getElementById('fCategory')?.value || '';
  const search= document.getElementById('fSearch')?.value || '';

  let url = '/api/expenses/?';
  if (year)   url += `year=${year}&`;
  if (month)  url += `month=${month}&`;
  if (catId)  url += `category=${catId}&`;
  if (search) url += `search=${encodeURIComponent(search)}&`;

  const res  = await fetch(url);
  const data = await res.json();
  const wrap = document.getElementById('expenseTableWrap');
  if (wrap) wrap.innerHTML = renderExpenseTableHTML(data.entries || []);
}

function yearOptions(currentYear) {
  let opts = '';
  for (let y = currentYear; y >= 2020; y--) {
    opts += `<option value="${y}" ${y===currentYear?'selected':''}>${y}</option>`;
  }
  return opts;
}

function getTopCategory(entries) {
  const totals = {};
  entries.forEach(e => {
    const key = e.category_name || 'Other';
    if (!totals[key]) totals[key] = {name:key, icon:e.category_icon||'💰', total:0};
    totals[key].total += e.amount;
  });
  const top = Object.values(totals).sort((a,b) => b.total-a.total)[0];
  return top || {name:'—', icon:'💰', total:0};
}

/* ── Expense Modal ──────────────────────────────────────────── */
async function showExpenseModal(expId) {
  let exp = null;
  if (expId) {
    const res = await fetch('/api/expenses/?');
    const all = (await res.json()).entries || [];
    exp = all.find(e => e.id === expId) || null;
  }

  const cats = window._expCategories || [];
  const curs = window._expCurrencies || [];
  const today = new Date().toISOString().split('T')[0];

  const catOpts = cats.map(c =>
    `<option value="${c.id}" ${exp && exp.category_id===c.id?'selected':''}>${c.icon} ${c.name}</option>`
  ).join('');
  const curOpts = curs.map(c =>
    `<option value="${c.id}" ${exp && exp.currency_code===c.code?'selected':c.code==='EGP'?'selected':''}>${c.flag} ${c.code}</option>`
  ).join('');
  const methOpts = PAYMENT_METHODS.map(m =>
    `<option value="${m}" ${exp && exp.payment_method===m?'selected':''}>${m}</option>`
  ).join('');

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title">${exp ? 'Edit' : 'Add'} Expense</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body"><div class="row g-3">
      <div class="col-sm-6">
        <label class="form-label">Date *</label>
        <input type="date" class="form-control" id="eDate" value="${exp ? exp.date : today}">
      </div>
      <div class="col-sm-6">
        <label class="form-label">Amount (EGP) *</label>
        <input type="number" step="0.01" min="0" class="form-control" id="eAmount"
               value="${exp ? exp.amount : ''}">
      </div>
      <div class="col-sm-6">
        <label class="form-label">Category</label>
        <select class="form-select" id="eCat" onchange="updateSubcategories()">${catOpts}</select>
      </div>
      <div class="col-sm-6">
        <label class="form-label">Subcategory</label>
        <select class="form-select" id="eSubcat">
          <option value="">— None —</option>
        </select>
      </div>
      <div class="col-12">
        <label class="form-label">Description</label>
        <input type="text" class="form-control" id="eDesc"
               value="${exp ? exp.description : ''}" placeholder="What was this expense?">
      </div>
      <div class="col-sm-6">
        <label class="form-label">Payment Method</label>
        <select class="form-select" id="eMethod">${methOpts}</select>
      </div>
      <div class="col-sm-6">
        <label class="form-label">Currency</label>
        <select class="form-select" id="eCurrency">${curOpts}</select>
      </div>
      <div class="col-12">
        <label class="form-label">Notes</label>
        <textarea class="form-control" id="eNotes" rows="2">${exp ? exp.notes : ''}</textarea>
      </div>
    </div></div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()">Cancel</button>
      <button class="btn-primary-custom" onclick="saveExpense(${expId || 'null'})">Save</button>
    </div>`);

  // Populate subcategories
  updateSubcategories(exp ? exp.subcategory_id : null);
}

function updateSubcategories(selectedSubId) {
  const catId = parseInt(document.getElementById('eCat')?.value);
  const sel   = document.getElementById('eSubcat');
  if (!sel) return;
  const cats  = window._expCategories || [];
  const cat   = cats.find(c => c.id === catId);
  sel.innerHTML = '<option value="">— None —</option>';
  if (cat && cat.subcategories) {
    cat.subcategories.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.name;
      if (selectedSubId && s.id === selectedSubId) opt.selected = true;
      sel.appendChild(opt);
    });
  }
}

async function saveExpense(expId) {
  const body = {
    date:           document.getElementById('eDate').value,
    amount:         parseFloat(document.getElementById('eAmount').value) || 0,
    category_id:    parseInt(document.getElementById('eCat').value) || null,
    subcategory_id: parseInt(document.getElementById('eSubcat').value) || null,
    description:    document.getElementById('eDesc').value.trim(),
    payment_method: document.getElementById('eMethod').value,
    currency_id:    parseInt(document.getElementById('eCurrency').value) || null,
    notes:          document.getElementById('eNotes').value.trim(),
  };
  const url    = expId ? `/api/expenses/${expId}/` : '/api/expenses/';
  const method = expId ? 'PUT' : 'POST';
  const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (res.ok) {
    closeModal(); showToast('Expense saved ✓', 'success'); renderExpenses();
  } else { showToast('Error saving expense', 'error'); }
}

async function deleteExpense(id) {
  if (!confirm('Delete this expense?')) return;
  await fetch(`/api/expenses/${id}/`, {method:'DELETE'});
  showToast('Deleted'); renderExpenses();
}

/* ── Export CSV ─────────────────────────────────────────────── */
async function exportExpenses() {
  const year  = document.getElementById('fYear')?.value || '';
  const month = document.getElementById('fMonth')?.value || '';
  let url = '/api/expenses/?';
  if (year)  url += `year=${year}&`;
  if (month) url += `month=${month}&`;
  const res  = await fetch(url);
  const data = await res.json();
  const rows = [['Date','Category','Subcategory','Description','Method','Amount','Notes']];
  (data.entries||[]).forEach(e => {
    rows.push([e.date, e.category_name, e.subcategory_name, e.description,
               e.payment_method, e.amount, e.notes]);
  });
  const csv  = rows.map(r => r.map(v => `"${String(v||'').replace(/"/g,'""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `expenses_${year}_${month}.csv`;
  a.click();
  showToast('CSV exported ✓', 'success');
}

/* ╔══════════════════════════════════════════════════════════╗
   ║  CATEGORIES MANAGEMENT PAGE                              ║
   ╚══════════════════════════════════════════════════════════╝ */
async function renderExpenseCategories() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = loadingHTML ? loadingHTML() : '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';
  const res  = await fetch('/api/expense-categories/');
  const data = await res.json();
  const cats = data.categories || [];
  window._expCategories = cats;

  const rows = cats.map(c => `
    <tr>
      <td style="font-size:20px;text-align:center;width:50px">${c.icon}</td>
      <td>
        <span style="font-weight:700">${c.name}</span>
        <div style="font-size:11px;color:var(--text-muted)">${(c.subcategories||[]).map(s=>s.name).join(' · ')}</div>
      </td>
      <td><input type="color" value="${c.color_hex}" title="Change colour"
                 onchange="patchCategoryColor(${c.id},this.value)" style="width:32px;height:32px;border:none;background:none;cursor:pointer"></td>
      <td class="text-center">${(c.subcategories||[]).length}</td>
      <td style="white-space:nowrap">
        <button class="btn-icon edit" onclick="showCategoryModal(${c.id})" title="Edit"><i class="bi bi-pencil"></i></button>
        <button class="btn-icon edit" onclick="showSubcategoryModal(${c.id})" title="Manage subcategories"><i class="bi bi-diagram-3"></i></button>
        <button class="btn-icon del"  onclick="deleteCategory(${c.id})" title="Delete"><i class="bi bi-trash"></i></button>
      </td>
    </tr>`).join('');

  mc.innerHTML = `
    <div class="page-header">
      <div><div class="page-title">📂 Expense Categories</div></div>
      <button class="btn-primary-custom" onclick="showCategoryModal(null)">
        <i class="bi bi-plus-lg"></i> Add Category
      </button>
    </div>
    <div class="table-container">
      <table class="data-table">
        <thead><tr>
          <th class="text-center">Icon</th>
          <th>Category</th>
          <th>Color</th>
          <th class="text-center">Subcategories</th>
          <th>Actions</th>
        </tr></thead>
        <tbody>${rows || '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text-muted)">No categories yet.</td></tr>'}</tbody>
      </table>
    </div>`;
}

async function showCategoryModal(catId) {
  let c = null;
  if (catId) {
    const res = await fetch('/api/expense-categories/');
    c = (await res.json()).categories.find(x => x.id === catId) || null;
  }
  showModal(`
    <div class="modal-header">
      <h5 class="modal-title">${c ? 'Edit' : 'Add'} Category</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body"><div class="row g-3">
      <div class="col-sm-8">
        <label class="form-label">Category Name *</label>
        <input type="text" class="form-control" id="catName" value="${c?c.name:''}" placeholder="e.g. Food">
      </div>
      <div class="col-sm-2">
        <label class="form-label">Icon</label>
        <input type="text" class="form-control" id="catIcon" value="${c?c.icon:'💰'}" maxlength="4"
               style="font-size:20px;text-align:center">
      </div>
      <div class="col-sm-2">
        <label class="form-label">Color</label>
        <input type="color" class="form-control" id="catColor" value="${c?c.color_hex:'#0d6efd'}">
      </div>
    </div></div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()">Cancel</button>
      <button class="btn-primary-custom" onclick="saveCategory(${catId||'null'})">Save</button>
    </div>`);
}

async function saveCategory(catId) {
  const body = {
    name:      document.getElementById('catName').value.trim(),
    icon:      document.getElementById('catIcon').value.trim() || '💰',
    color_hex: document.getElementById('catColor').value,
  };
  if (!body.name) { showToast('Name required','error'); return; }
  const url = catId ? `/api/expense-categories/${catId}/` : '/api/expense-categories/';
  const method = catId ? 'PUT' : 'POST';
  const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (res.ok) { closeModal(); showToast('Category saved ✓','success'); renderExpenseCategories(); }
  else showToast('Error','error');
}

async function patchCategoryColor(id, hex) {
  await fetch(`/api/expense-categories/${id}/`, {method:'PUT',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify({color_hex:hex})});
}

async function deleteCategory(id) {
  if (!confirm('Delete this category and all its subcategories?')) return;
  await fetch(`/api/expense-categories/${id}/`, {method:'DELETE'});
  showToast('Deleted'); renderExpenseCategories();
}

async function showSubcategoryModal(catId) {
  const res  = await fetch('/api/expense-categories/');
  const cats = (await res.json()).categories || [];
  const cat  = cats.find(c => c.id === catId);
  if (!cat) return;
  const subRows = (cat.subcategories||[]).map(s => `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <input type="text" class="form-control form-control-sm" value="${s.name}"
             id="sub_${s.id}" style="flex:1">
      <button class="btn-icon edit" onclick="saveSubcategory(${s.id})" title="Save">
        <i class="bi bi-floppy"></i></button>
      <button class="btn-icon del" onclick="deleteSubcategory(${s.id},${catId})" title="Delete">
        <i class="bi bi-trash"></i></button>
    </div>`).join('');

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title">${cat.icon} ${cat.name} — Subcategories</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body">
      <div id="subList">${subRows || '<p style="color:var(--text-muted)">No subcategories yet.</p>'}</div>
      <hr style="border-color:var(--border-color)">
      <div style="display:flex;gap:8px;margin-top:10px">
        <input type="text" class="form-control form-control-sm" id="newSubName"
               placeholder="New subcategory name" style="flex:1">
        <button class="btn-primary-custom" onclick="addSubcategory(${catId})" style="padding:5px 14px;font-size:13px">
          <i class="bi bi-plus-lg"></i> Add
        </button>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()">Close</button>
    </div>`);
}

async function addSubcategory(catId) {
  const name = document.getElementById('newSubName')?.value.trim();
  if (!name) { showToast('Name required','error'); return; }
  const res = await fetch('/api/expense-subcategories/', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({category_id: catId, name})});
  if (res.ok) {
    showToast('Subcategory added ✓','success');
    const cat = (window._expCategories||[]).find(c=>c.id===catId);
    if (cat) showSubcategoryModal(catId);
    // Refresh categories
    const catRes = await fetch('/api/expense-categories/');
    window._expCategories = (await catRes.json()).categories || [];
  } else showToast('Error','error');
}

async function saveSubcategory(subId) {
  const name = document.getElementById(`sub_${subId}`)?.value.trim();
  if (!name) return;
  await fetch(`/api/expense-subcategories/${subId}/`, {method:'PUT',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})});
  showToast('Saved ✓','success');
}

async function deleteSubcategory(subId, catId) {
  if (!confirm('Delete this subcategory?')) return;
  await fetch(`/api/expense-subcategories/${subId}/`, {method:'DELETE'});
  showToast('Deleted');
  showSubcategoryModal(catId);
}

window.renderExpenses           = renderExpenses;
window.renderExpenseCategories  = renderExpenseCategories;
window.showExpenseModal         = showExpenseModal;
window.saveExpense              = saveExpense;
window.deleteExpense            = deleteExpense;
window.applyExpenseFilters      = applyExpenseFilters;
window.exportExpenses           = exportExpenses;
window.updateSubcategories      = updateSubcategories;
window.showCategoryModal        = showCategoryModal;
window.saveCategory             = saveCategory;
window.patchCategoryColor       = patchCategoryColor;
window.deleteCategory           = deleteCategory;
window.showSubcategoryModal     = showSubcategoryModal;
window.addSubcategory           = addSubcategory;
window.saveSubcategory          = saveSubcategory;
window.deleteSubcategory        = deleteSubcategory;
