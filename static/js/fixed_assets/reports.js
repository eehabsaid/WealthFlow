"use strict";
// Fixed assets reports tab — render, scope toggle, and PDF/Excel download.
// Split out of analytics.js (200-line backlog). Bare globals — called by
// fixed_assets/tabs.js and fixed_assets/index.js.
// ════════════════════════════════════════════════════════════════════════════

function renderFixedAssetsReports(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = normalizeFixedAssetsData(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">🗂️</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_reports_empty">No Reports Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_reports_empty_desc">Add fixed assets to generate reports.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const options = assetsArray
    .map((asset) => `<option value="${asset.id}">${asset.name || "—"}</option>`)
    .join("");

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr);gap:16px;align-items:start;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-size:18px;font-weight:700;margin-bottom:8px;" data-i18n="fixed_assets_reports_title"></div>
        <div class="fixed-assets-section-note" style="font-size:13px;margin-bottom:18px;" data-i18n="fixed_assets_reports_subtitle"></div>

        <div class="row g-3 mb-3">
          <div class="col-md-6">
            <label class="form-label text-light" data-i18n="report_scope"></label>
            <select class="form-select" id="fixedAssetsReportScope" onchange="toggleFixedAssetsReportScope()">
              <option value="single" data-i18n="single_asset">Single Asset</option>
              <option value="portfolio" data-i18n="entire_portfolio">Entire Portfolio</option>
            </select>
          </div>
          <div class="col-md-6" id="fixedAssetsReportAssetWrap">
            <label class="form-label text-light" data-i18n="select_asset"></label>
            <select class="form-select" id="fixedAssetsReportAsset">
              ${options}
            </select>
          </div>
        </div>

        <div class="d-flex flex-wrap gap-2">
          <button class="btn-primary-custom" onclick="downloadFixedAssetsReport('pdf')">
            <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
          </button>
          <button class="btn-secondary-custom" onclick="downloadFixedAssetsReport('excel')">
            <i class="bi bi-file-earmark-excel"></i> <span data-i18n="download_excel">Download Excel Workbook</span>
          </button>
        </div>
      </div>

      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:12px;" data-i18n="report_contents"></div>
        <div style="display:grid;gap:10px;">
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_general_property"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_photos_renovations"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_furniture_valuations"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_sale_info"></div>
        </div>
      </div>
    </div>
  `;

  const scopeField = document.getElementById("fixedAssetsReportScope");
  if (scopeField) {
    scopeField.value = "single";
  }

  applyTranslations();
  toggleFixedAssetsReportScope();
}

function toggleFixedAssetsReportScope() {
  const scopeField = document.getElementById("fixedAssetsReportScope");
  const assetWrap = document.getElementById("fixedAssetsReportAssetWrap");
  const isSingle = scopeField?.value !== "portfolio";

  if (assetWrap) {
    assetWrap.style.display = isSingle ? "block" : "none";
  }
}

async function downloadFixedAssetsReport(format) {
  const scope = document.getElementById("fixedAssetsReportScope")?.value || "single";
  const assetId = document.getElementById("fixedAssetsReportAsset")?.value || "";

  if (scope === "single" && !assetId) {
    showToast(t("report_asset_required", "Please select an asset first."), "warning");
    return;
  }

  const btn = event?.currentTarget || event?.target;
  const loadingText = t("generating", "Generating...");
  const originalHtml = btn?.innerHTML;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${loadingText}`;
  }

  try {
    const params = new URLSearchParams({
      scope,
      lang: currentLang(),
    });

    if (scope === "single") {
      params.set("asset_id", assetId);
    }

    const endpoint =
      format === "pdf" ? "/api/fixed-assets/reports/pdf/" : "/api/fixed-assets/reports/excel/";

    const response = await fetch(`${endpoint}?${params.toString()}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || t("download_report_failed", "Failed to download report."));
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const fileNameMatch = disposition.match(/filename="(.+)"/);

    anchor.href = url;
    anchor.download =
      fileNameMatch?.[1] || `fixed_assets_report.${format === "pdf" ? "pdf" : "xlsx"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}
