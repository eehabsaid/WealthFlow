"use strict";
// index.js — thin window.* export aggregator for the expenses module.
// Split out of the original expenses/index.js monolith to stay under the
// 200-line-per-file ceiling. Structural split only - no logic changes.
//
// Siblings (loaded before this file, in templates/index.html):
// - utils.js, api.js, reports.js, categories.js, subcategories.js, modal.js
//   (pre-existing, unchanged)
// - dashboard.js: KPI constants + renderExpenses() main page render.
// - table.js: renderExpenseTableHTML() - entries table rendering.
// - filters.js: applyExpenseFilters() - filter-bar handler.
//
// This file must remain the last expenses/*.js script tag - it only
// re-exports functions already defined by the files above onto window.

window.renderExpenses = renderExpenses;
window.renderExpenseCategories = renderExpenseCategories;
window.showExpenseModal = showExpenseModal;
window.showReadonlyExpenseModal = showReadonlyExpenseModal;
window.saveExpense = saveExpense;
window.deleteExpense = deleteExpense;
window.toggleExpenseBankField = toggleExpenseBankField;
window.applyExpenseFilters = applyExpenseFilters;
window.exportExpenses = exportExpenses;
window.updateSubcategories = updateSubcategories;
window.showCategoryModal = showCategoryModal;
window.saveCategory = saveCategory;
window.patchCategoryColor = patchCategoryColor;
window.deleteCategory = deleteCategory;
window.showSubcategoryModal = showSubcategoryModal;
window.addSubcategory = addSubcategory;
window.saveSubcategory = saveSubcategory;
window.deleteSubcategory = deleteSubcategory;
