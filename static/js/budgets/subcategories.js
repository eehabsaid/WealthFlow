"use strict";

// Recurring transaction form: the Subcategory list depends on the chosen Category, exactly like the Expenses form.
function updateRecurringSubcategories(selectedSubId) {
  const catId = parseInt(document.getElementById("rCat")?.value);
  const sel = document.getElementById("rSubcat");
  if (!sel) return;
  const cat = (window._expCategories || []).find((c) => c.id === catId);
  sel.innerHTML = '<option value="" data-i18n="none_option">— None —</option>';
  ((cat && cat.subcategories) || []).forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.name;
    if (selectedSubId && s.id === selectedSubId) opt.selected = true;
    sel.appendChild(opt);
  });
  applyTranslations();
}
