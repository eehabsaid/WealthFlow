"use strict";

function showLoading() {
  const el = document.querySelector(".spinner-overlay");
  if (el) el.style.display = "flex";
}

function hideLoading() {
  const el = document.querySelector(".spinner-overlay");
  if (el) el.style.display = "none";
}

function loadingHTML() {
  return `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Loading...</p>
        </div>`;
}

// ════════════════════════════════════════════════════════════════════════════
// MOBILE SIDEBAR
// ════════════════════════════════════════════════════════════════════════════
