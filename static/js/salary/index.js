"use strict";
// index.js — re-exports all public functions onto window for HTML backward
// compatibility. Must be loaded LAST after all other module files.
// Content split into employment_page.js, year_pills.js, and MONTHS moved to
// utils.js (200-line rule). Do not edit directly.

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
