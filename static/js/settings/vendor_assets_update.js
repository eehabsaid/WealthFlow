"use strict";
// Vendor Assets Update card — Settings > Backup & Restore
// Lets an admin manually refresh the locally vendored copies of
// third-party frontend libraries (Bootstrap, Chart.js, Leaflet, Google
// Fonts) that make WealthFlow work fully offline. Requires internet
// access at the moment the button is pressed; on failure the existing
// working local assets are left untouched (handled server-side).

function renderVendorAssetsUpdateCard() {
  return `
    <div class="col-12 mt-4">
        <div class="card card-custom" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
            <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="vendor_assets_update_title">Offline Assets Update</h5>
            <p class="small mb-3" style="color: var(--text-secondary) !important;" data-i18n="vendor_assets_update_desc">
                WealthFlow runs fully offline by default, using local copies of Bootstrap, Chart.js, Leaflet, and fonts. Use this button to check for newer versions when you have an internet connection — it only downloads if an update is actually available, and keeps your current working copies if anything fails.
            </p>
            <button class="btn-secondary-custom py-2 justify-content-center" id="vendorAssetsUpdateBtn" onclick="updateVendorAssets()" style="width:fit-content;">
                <i class="bi bi-cloud-arrow-down me-2"></i>
                <span data-i18n="btn_update_vendor_assets">Check for Updates</span>
            </button>
        </div>
    </div>`;
}

async function updateVendorAssets() {
  const btn = document.getElementById("vendorAssetsUpdateBtn");
  if (!btn) return;

  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span><span data-i18n="vendor_assets_checking">Checking for updates...</span>`;

  try {
    const res = await fetch("/api/settings/vendor-assets/update/", { method: "POST" });
    const data = await res.json();

    if (data.success && data.updated) {
      showToast(t("vendor_assets_update_success", "Offline assets updated successfully."), "success");
    } else if (data.success && !data.updated) {
      showToast(t("vendor_assets_already_current", "Already up to date. Nothing was downloaded."), "success");
    } else {
      const failMsg = t("vendor_assets_update_failed", "Update failed. Existing assets were kept.");
      showToast(data.message ? `${failMsg} (${data.message})` : failMsg, "error");
    }
  } catch (e) {
    showToast(t("vendor_assets_update_failed", "Update failed. Existing assets were kept."), "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    applyTranslations();
  }
}
