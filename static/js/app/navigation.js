"use strict";

function navigate(route) {
  localStorage.setItem("wf_last_route", route);
  window.location.hash = route;
  closeMobileSidebar();
  // Force hash re-trigger in case hash hasn't changed
  setTimeout(() => {
    window.location.hash = route;
  }, 50);
}

function triggerAddEntry() {
  const hash = window.location.hash.replace("#", "");
  if (
    hash === "employment" ||
    hash === "salary" ||
    hash.startsWith("employment-") ||
    hash.startsWith("salary-")
  ) {
    const cId =
      typeof window.getCurrentEmploymentCompanyId === "function"
        ? window.getCurrentEmploymentCompanyId()
        : null;
    const targetCompanyId = cId || (hash.includes("-") ? parseInt(hash.split("-")[1]) : null);
    showSalaryModal(null, targetCompanyId);
  } else if (hash === "balance") showBalanceModal(null);
  else if (hash === "bank-certificates") showBankCertificateModal(null);
  else if (hash === "fixed-assets") showFixedAssetModal();
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL
// ════════════════════════════════════════════════════════════════════════════

function toggleSection(el) {
  const content = el.nextElementSibling;
  const icon = el.querySelector(".chevron-icon");
  const closed = content.style.display === "none";
  content.style.display = closed ? "block" : "none";
  icon?.classList.toggle("bi-chevron-down", closed);
  icon?.classList.toggle("bi-chevron-right", !closed);
}

// ════════════════════════════════════════════════════════════════════════════
// AUTH — LOGOUT, PROFILE MODAL, AVATAR UPLOAD
// ════════════════════════════════════════════════════════════════════════════
