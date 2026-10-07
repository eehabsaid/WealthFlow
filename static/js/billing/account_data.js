"use strict";
// "My data" card on the customer plans page: export everything I own, or delete my account.
// Lives on the plans page on purpose: a lapsed user is locked to that page and must still be able to do both.
// Backend: /api/account/export/ and /api/account/delete/ (exempt from the subscription lock).

function renderAccountDataCard() {
  const host = document.getElementById("wf-account-data");
  if (!host) return;
  host.innerHTML = `
    <div class="wf-account-card">
      <h2 data-i18n="account_data_title">${t("account_data_title", "Your data")}</h2>
      <p data-i18n="account_data_subtitle">${t("account_data_subtitle", "Download a copy of everything you own in WealthFlow, or permanently delete your account.")}</p>
      <div class="wf-account-actions">
        <button class="btn btn-outline-primary" id="wf-account-export-btn" onclick="exportMyData()" data-i18n="account_data_export_btn">${t("account_data_export_btn", "Export my data")}</button>
        <button class="btn btn-outline-danger" id="wf-account-delete-btn" onclick="toggleDeleteAccountForm(true)" data-i18n="account_data_delete_btn">${t("account_data_delete_btn", "Delete my account")}</button>
      </div>
      <div id="wf-account-delete-form" class="wf-account-delete-form" hidden>
        <p class="wf-account-warning" data-i18n="account_data_delete_warning">${t("account_data_delete_warning", "This is permanent and cannot be undone. Your profile, balances, expenses, assets, documents and AI chats are deleted. Export your data first if you want to keep a copy.")}</p>
        <label for="wf-account-password" data-i18n="account_data_password_label">${t("account_data_password_label", "Your password")}</label>
        <input type="password" id="wf-account-password" class="form-control" autocomplete="current-password" />
        <label for="wf-account-confirm" data-i18n="account_data_confirm_label">${t("account_data_confirm_label", "Type DELETE to confirm")}</label>
        <input type="text" id="wf-account-confirm" class="form-control" autocomplete="off" />
        <div class="wf-account-actions">
          <button class="btn btn-danger" id="wf-account-delete-confirm-btn" onclick="deleteMyAccount()" data-i18n="account_data_delete_confirm_btn">${t("account_data_delete_confirm_btn", "Permanently delete")}</button>
          <button class="btn btn-secondary" onclick="toggleDeleteAccountForm(false)" data-i18n="account_data_cancel_btn">${t("account_data_cancel_btn", "Cancel")}</button>
        </div>
      </div>
    </div>`;
}

function toggleDeleteAccountForm(show) {
  const form = document.getElementById("wf-account-delete-form");
  if (form) form.hidden = !show;
  if (!show) {
    const pw = document.getElementById("wf-account-password");
    const cf = document.getElementById("wf-account-confirm");
    if (pw) pw.value = "";
    if (cf) cf.value = "";
  }
}

async function exportMyData() {
  const btn = document.getElementById("wf-account-export-btn");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/account/export/", { credentials: "same-origin" });
    if (!res.ok) throw new Error("export failed");
    const blob = await res.blob();
    const match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = match ? match[1] : "wealthflow-my-data.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    showToast(t("account_data_export_done", "Your data was downloaded ✓"), "success");
  } catch (e) {
    showToast(
      t("account_data_export_failed", "Couldn't export your data. Please try again."),
      "error"
    );
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteMyAccount() {
  const password = document.getElementById("wf-account-password")?.value || "";
  const confirmText = (document.getElementById("wf-account-confirm")?.value || "").trim();
  if (confirmText !== "DELETE") {
    showToast(t("account_data_confirm_required", "Type DELETE to confirm."), "error");
    return;
  }
  const btn = document.getElementById("wf-account-delete-confirm-btn");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/account/delete/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
      body: JSON.stringify({ confirm: confirmText, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(t("account_data_deleted", "Your account was deleted."), "success");
      setTimeout(() => (window.location.href = "/accounts/login/"), 1200);
      return;
    }
    const reasons = {
      invalid_password: t("account_data_wrong_password", "Wrong password."),
      last_admin: t(
        "account_data_last_admin",
        "You are the only administrator. Make another user an administrator first."
      ),
      confirmation_required: t("account_data_confirm_required", "Type DELETE to confirm."),
    };
    showToast(
      reasons[data.error] ||
        t("account_data_delete_failed", "Couldn't delete the account. Please try again."),
      "error"
    );
  } catch (e) {
    showToast(
      t("account_data_delete_failed", "Couldn't delete the account. Please try again."),
      "error"
    );
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.renderAccountDataCard = renderAccountDataCard;
window.toggleDeleteAccountForm = toggleDeleteAccountForm;
window.exportMyData = exportMyData;
window.deleteMyAccount = deleteMyAccount;
