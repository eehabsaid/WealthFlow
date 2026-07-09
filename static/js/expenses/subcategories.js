'use strict';

function updateSubcategories(selectedSubId) {
  const catId = parseInt(document.getElementById("eCat")?.value);
  const sel = document.getElementById("eSubcat");
  if (!sel) return;
  const cats = window._expCategories || [];
  const cat = cats.find((c) => c.id === catId);
  sel.innerHTML = '<option value="" data-i18n="none_option">— None —</option>';
  if (cat && cat.subcategories) {
    cat.subcategories.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      if (selectedSubId && s.id === selectedSubId) opt.selected = true;
      sel.appendChild(opt);
    });
  }
  applyTranslations();
}

async function showSubcategoryModal(catId) {
  const res = await fetch("/api/expense-categories/");
  const cats = (await res.json()).categories || [];
  const cat = cats.find((c) => c.id === catId);
  if (!cat) return;
  const subRows = (cat.subcategories || [])
    .map(
      (s) => `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <input type="text" class="form-control form-control-sm" value="${s.name}"
             id="sub_${s.id}" style="flex:1">
      <button class="btn-icon edit" onclick="saveSubcategory(${s.id})" title="Save">
        <i class="bi bi-floppy"></i></button>
      <button class="btn-icon del" onclick="deleteSubcategory(${s.id},${catId})" title="Delete">
        <i class="bi bi-trash"></i></button>
    </div>`,
    )
    .join("");

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title">${cat.icon} ${cat.name} - <span data-i18n="subcategories">Subcategories</span></h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body">
      <div id="subList">${subRows || '<p style="color:var(--text-muted)" data-i18n="no_subcategories_yet">No subcategories yet.</p>'}</div>
      <hr style="border-color:var(--border-color)">
      <div style="display:flex;gap:8px;margin-top:10px">
        <input type="text" class="form-control form-control-sm" id="newSubName"
               placeholder="New subcategory name" data-i18n-placeholder="new_subcategory_placeholder" style="flex:1">
        <button class="btn-primary-custom" onclick="addSubcategory(${catId})" style="padding:5px 14px;font-size:13px">
          <i class="bi bi-plus-lg"></i> <span data-i18n="btn_add">Add</span>
        </button>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="close_button">Close</button>
    </div>`);
  applyTranslations();
}

async function addSubcategory(catId) {
  const name = document.getElementById("newSubName")?.value.trim();
  if (!name) {
    showToast("Name required", "error");
    return;
  }
  const res = await fetch("/api/expense-subcategories/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category_id: catId, name }),
  });
  if (res.ok) {
    showToast("Subcategory added ✓", "success");
    const cat = (window._expCategories || []).find((c) => c.id === catId);
    if (cat) showSubcategoryModal(catId);
    // Refresh categories
    const catRes = await fetch("/api/expense-categories/");
    window._expCategories = (await catRes.json()).categories || [];
  } else showToast("Error", "error");
}

// ════════════════════════════════════════════════════════════════════════════
// SUBCATEGORY MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════