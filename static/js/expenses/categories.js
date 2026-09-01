"use strict";

async function renderExpenseCategories() {
  const mc = document.getElementById("main-content");
  mc.innerHTML = loadingHTML
    ? loadingHTML()
    : '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';
  const res = await fetch("/api/expense-categories/");
  const data = await res.json();
  const cats = data.categories || [];
  window._expCategories = cats;

  const rows = cats
    .map(
      (c) => `
    <tr>
      <td style="font-size:20px;text-align:center;width:50px">${c.icon}</td>
      <td>
        <span style="font-weight:700">${c.name}</span>
        <div style="font-size:11px;color:var(--text-muted)">${(c.subcategories || []).map((s) => s.name).join(" · ")}</div>
      </td>
      <td><input type="color" value="${c.color_hex}" title="Change colour"
                 onchange="patchCategoryColor(${c.id},this.value)" style="width:32px;height:32px;border:none;background:none;cursor:pointer"></td>
      <td class="text-center">${(c.subcategories || []).length}</td>
      <td style="white-space:nowrap">
        <button class="btn-icon edit" onclick="showCategoryModal(${c.id})" title="Edit"><i class="bi bi-pencil"></i></button>
        <button class="btn-icon edit" onclick="showSubcategoryModal(${c.id})" title="Manage subcategories"><i class="bi bi-diagram-3"></i></button>
        <button class="btn-icon del"  onclick="deleteCategory(${c.id})" title="Delete"><i class="bi bi-trash"></i></button>
      </td>
    </tr>`
    )
    .join("");

  mc.innerHTML = `
    <div class="page-header">
      <div><div class="page-title">📂 <span data-i18n="expense_categories">Expense Categories</span></div></div>
      <button class="btn-primary-custom" onclick="showCategoryModal(null)">
        <i class="bi bi-plus-lg"></i> <span data-i18n="add_category">Add Category</span>
      </button>
    </div>
    <div class="table-container">
      <table class="data-table">
        <thead><tr>
          <th class="text-center" data-i18n="icon">Icon</th>
          <th data-i18n="category">Category</th>
          <th data-i18n="color">Color</th>
          <th class="text-center" data-i18n="subcategories">Subcategories</th>
          <th data-i18n="actions">Actions</th>
        </tr></thead>
        <tbody>${rows || '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text-muted)" data-i18n="no_categories_yet">No categories yet.</td></tr>'}</tbody>
      </table>
    </div>`;
  applyTranslations();
}

async function showCategoryModal(catId) {
  let c = null;
  if (catId) {
    const res = await fetch("/api/expense-categories/");
    c = (await res.json()).categories.find((x) => x.id === catId) || null;
  }
  showModal(`
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="${c ? "edit_category" : "add_category"}">${c ? "Edit" : "Add"} Category</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body"><div class="row g-3">
      <div class="col-sm-8">
        <label class="form-label"><span data-i18n="category_name">Category Name</span> *</label>
        <input type="text" class="form-control" id="catName" value="${c ? c.name : ""}" placeholder="e.g. Food" data-i18n-placeholder="category_name_placeholder">
      </div>
      <div class="col-sm-2">
        <label class="form-label" data-i18n="icon">Icon</label>
        <input type="text" class="form-control" id="catIcon" value="${c ? c.icon : "💰"}" maxlength="4"
               style="font-size:20px;text-align:center">
      </div>
      <div class="col-sm-2">
        <label class="form-label" data-i18n="color">Color</label>
        <input type="color" class="form-control" id="catColor" value="${c ? c.color_hex : "#0d6efd"}">
      </div>
    </div></div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="btn_cancel">Cancel</button>
      <button class="btn-primary-custom" onclick="saveCategory(${catId || "null"})" data-i18n="btn_save">Save</button>
    </div>`);
  applyTranslations();
}
