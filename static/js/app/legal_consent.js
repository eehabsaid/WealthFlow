"use strict";
// Re-consent prompt: when a sysadmin publishes a legal version flagged "require
// re-consent", each account sees this blocking dialog once after login until it
// accepts (or signs out). Accounts are otherwise never asked again.

const LEGAL_CONSENT_DELAY_MS = 1500;
const LEGAL_CONSENT_MAX_ATTEMPTS = 20;

function legalConsentModalOpen() {
  return !!document.querySelector(".modal.show, .modal-backdrop");
}

// Runs after the first screen has settled and never on top of another dialog
// (first-run wizard, any modal being opened or closed): while one is open the
// check is postponed, then made once it is gone. The delay keeps the extra
// request off the critical boot path.
async function checkLegalConsent(attempt = 0) {
  await new Promise((resolve) => setTimeout(resolve, LEGAL_CONSENT_DELAY_MS));
  if (legalConsentModalOpen()) {
    if (attempt + 1 < LEGAL_CONSENT_MAX_ATTEMPTS) checkLegalConsent(attempt + 1);
    return;
  }
  let status;
  try {
    const res = await fetch("/api/legal/consent/");
    if (!res.ok) return;
    status = await res.json();
  } catch (e) {
    return;
  }
  if (!status.required || document.getElementById("legalConsentOverlay")) return;
  const el = document.createElement("div");
  el.id = "legalConsentOverlay";
  el.className = "modal-backdrop-lite";
  el.style.cssText =
    "position:fixed;inset:0;z-index:2000;display:flex;align-items:center;justify-content:center;background:rgb(0 0 0 / 70%);padding:16px";
  el.innerHTML = `
    <div role="dialog" aria-modal="true" style="max-width:480px;width:100%;background:var(--bg-secondary);
         border:1px solid var(--border-color);border-radius:14px;padding:22px">
      <h3 style="margin:0 0 8px" data-i18n="legal_consent_title">Updated Terms and Privacy Policy</h3>
      <p data-i18n="legal_consent_body">We updated our Terms of Service and Privacy Policy. Please review and accept them to continue.</p>
      <div class="legal-consent-links">
        <a href="/terms/" target="_blank" rel="noopener" data-i18n="legal_terms_title">Terms of Service</a>
        <a href="/privacy/" target="_blank" rel="noopener" data-i18n="legal_privacy_title">Privacy Policy</a>
      </div>
      <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end">
        <button type="button" class="btn-secondary-custom" onclick="doLogout()" data-i18n="nav_logout">Logout</button>
        <button type="button" id="legalConsentAccept" class="btn-primary-custom" data-i18n="legal_consent_accept">I accept</button>
      </div>
    </div>`;
  document.body.appendChild(el);
  applyTranslations();
  document.getElementById("legalConsentAccept").addEventListener("click", async () => {
    const res = await fetch("/api/legal/consent/", { method: "POST" });
    if (res.ok) el.remove();
  });
}

window.checkLegalConsent = checkLegalConsent;
