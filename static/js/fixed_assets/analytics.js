"use strict";
// Fixed assets analytics and reports tab rendering
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssetsAnalytics(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = buildDashboardAnalyticsAssets(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">📊</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_analytics_empty">No Analytics Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_analytics_empty_desc">Add fixed assets to calculate analytics.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const metrics = getFixedAssetsAnalyticsMetrics(assetsArray);

  const portfolioCards = renderFixedAssetsPortfolioCards(metrics, fixedAssetsState.portfolioSnapshot);
  const tableRows = metrics.assetRows.length
    ? metrics.assetRows.map((row) => `
      <tr>
        <td class="fixed-assets-card-title">${row.name}</td>
        <td data-i18n="${fixedAssetTypeToI18nKey(row.type)}">${row.type}</td>
        <td class="text-end">${fmtpresent(row.roi)}%</td>
        <td class="text-end">${fmtpresent(row.appreciation)}%</td>
        <td class="text-end">${fmtpresent(row.annualReturn)}%</td>
        <td class="text-end">${row.holdingPeriodLabel}</td>
        <td class="text-end">${fmtpresent(row.renovationCostPercent)}%</td>
        <td class="text-end ${row.gainAmount >= 0 ? "text-success" : "text-danger"}">${fmt(row.gainAmount)}</td>
      </tr>
    `).join("")
    : _noDataFixedAssets(8);

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
      ${portfolioCards}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:20px;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="liquid_vs_fixed_assets"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsLiquidVsFixedChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="asset_performance"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsPerformanceChart"></canvas></div>
      </div>
    </div>

    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden;">
      <div class="fixed-assets-section-title" style="padding:14px 20px;font-weight:700;border-bottom:1px solid var(--border-color);" data-i18n="per_asset_analytics"></div>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">Asset Name</th>
              <th data-i18n="asset_type">Asset Type</th>
              <th class="text-end" data-i18n="roi">ROI</th>
              <th class="text-end" data-i18n="appreciation_percent">Appreciation %</th>
              <th class="text-end" data-i18n="annual_return">Annual Return</th>
              <th class="text-end" data-i18n="holding_period">Holding Period</th>
              <th class="text-end" data-i18n="renovation_cost_percent">Renovation Cost %</th>
              <th class="text-end" data-i18n="gain_amount">Gain Amount</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;

  applyTranslations();
  drawFixedAssetsAnalyticsCharts(metrics, fixedAssetsState.portfolioSnapshot);
}

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
      format === "pdf"
        ? "/api/fixed-assets/reports/pdf/"
        : "/api/fixed-assets/reports/excel/";

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

function renderFixedAssetsPortfolioCards(metrics, snapshot) {
  const fixedValueCard = renderFixedAssetsKpi(
    "bi bi-bank2",
    "total_fixed_assets_value",
    fmt(metrics.totalFixedAssetsValue),
  );

  if (!snapshot) {
    return `
      ${fixedValueCard}
      ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", "...")}
      ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", "...")}
      ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
    `;
  }

  const liquidVsFixedLabel = `${fmtpresent(snapshot.liquidAssetsRatio)}% / ${fmtpresent(snapshot.fixedAssetsRatio)}%`;

  return `
    ${fixedValueCard}
    ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", `${fmtpresent(snapshot.netWorthContribution)}%`)}
    ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", liquidVsFixedLabel)}
    ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
  `;
}

function getFixedAssetsAnalyticsMetrics(assets) {
  const now = new Date();
  const assetRows = assets.map((asset) => {
    const purchasePrice = parseFloat(asset.purchase_price) || 0;
    const currentValue = parseFloat(asset.current_market_value) || 0;
    const renovationCost = asset.total_renovation_costs !== undefined ? asset.total_renovation_costs : (asset.renovations || []).reduce(
      (sum, item) => sum + (parseFloat(item.amount_egp) || 0),
      0,
    );
    const acquisitionCost = asset.total_acquisition_costs !== undefined ? asset.total_acquisition_costs : 0;
    const investmentBase = asset.total_investment !== undefined ? asset.total_investment : (purchasePrice + renovationCost + acquisitionCost);

    const gainAmount = asset.gain_loss !== undefined ? asset.gain_loss : (currentValue - investmentBase);
    const roi = asset.roi !== undefined ? asset.roi : (investmentBase > 0 ? (gainAmount / investmentBase) * 100 : 0);
    const appreciation = asset.appreciation !== undefined ? asset.appreciation : (investmentBase > 0 ? (gainAmount / investmentBase) * 100 : 0);

    const purchaseDate = asset.purchase_date ? new Date(asset.purchase_date) : null;
    const holdingYearsRaw = purchaseDate ? (now - purchaseDate) / (1000 * 60 * 60 * 24 * 365.25) : 0;
    const holdingYears = holdingYearsRaw > 0 ? holdingYearsRaw : 0;
    const annualReturn = asset.annual_return !== undefined ? asset.annual_return : (
      investmentBase > 0 && holdingYears > 0
        ? (Math.pow(currentValue / investmentBase, 1 / holdingYears) - 1) * 100
        : 0
    );
    const holdingMonths = purchaseDate
      ? Math.max(0, Math.round((now - purchaseDate) / (1000 * 60 * 60 * 24 * 30.4375)))
      : 0;
    const renovationCostPercent = purchasePrice > 0 ? (renovationCost / purchasePrice) * 100 : 0;

    return {
      name: asset.name || "—",
      type: asset.asset_type || t("type_other", "Other"),
      roi,
      appreciation,
      annualReturn: Number.isFinite(annualReturn) ? annualReturn : 0,
      holdingPeriodMonths: holdingMonths,
      holdingPeriodLabel: formatHoldingPeriod(holdingMonths),
      renovationCostPercent,
      gainAmount,
      currentValue,
    };
  });

  const totalFixedAssetsValue = assetRows.reduce((sum, row) => sum + row.currentValue, 0);
  const shares = assetRows
    .map((row) => (totalFixedAssetsValue > 0 ? row.currentValue / totalFixedAssetsValue : 0))
    .filter((share) => share > 0);
  const concentration = shares.reduce((sum, share) => sum + share * share, 0);
  const diversificationScore = shares.length > 1
    ? Math.max(0, ((1 - concentration) / (1 - 1 / shares.length)) * 100)
    : shares.length === 1 ? 0 : 100;

  return {
    totalFixedAssetsValue,
    diversificationScore,
    assetRows,
  };
}

function formatHoldingPeriod(months) {
  if (!months) {
    return `0 ${t("months", "Months")}`;
  }

  if (months < 12) {
    return `${months} ${t("months", "Months")}`;
  }

  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;

  if (!remainingMonths) {
    return `${years} ${t("years", "Years")}`;
  }

  return `${years} ${t("years", "Years")} ${remainingMonths} ${t("months", "Months")}`;
}

async function loadFixedAssetsPortfolioSnapshot() {
  fixedAssetsState.portfolioSnapshotLoading = true;

  try {
    const response = await fetch("/api/fixed-assets/");
    if (!response.ok) throw new Error("Failed to load analytics snapshot");

    const data = await response.json();
    fixedAssetsState.portfolioSnapshot = data?.portfolio_snapshot || null;
  } catch (err) {
    fixedAssetsState.portfolioSnapshot = null;
    console.error(err);
  } finally {
    fixedAssetsState.portfolioSnapshotLoading = false;
    if (fixedAssetsState.activeTab === "analytics") {
      renderActiveFixedAssetsTab();
    }
  }
}

function drawFixedAssetsAnalyticsCharts(metrics, snapshot) {
  const liquidValue = snapshot?.liquidAssetsValue || 0;
  const fixedValue = snapshot?.fixedAssetsValue || metrics.totalFixedAssetsValue;

  drawFixedAssetsDoughnutChart(
    "fixedAssetsLiquidVsFixedChart",
    [t("liquid_assets", "Liquid Assets"), t("fixed_assets", "Fixed Assets")],
    [liquidValue, fixedValue],
  );

  const performanceRows = [...metrics.assetRows]
    .sort((a, b) => b.roi - a.roi)
    .slice(0, 8);

  drawFixedAssetsBarChart(
    "fixedAssetsPerformanceChart",
    performanceRows.map((row) => row.name),
    [
      {
        label: t("roi", "ROI"),
        data: performanceRows.map((row) => row.roi),
        color: "#1a6ef5",
      },
      {
        label: t("annual_return", "Annual Return"),
        data: performanceRows.map((row) => row.annualReturn),
        color: "#10b981",
      },
    ],
  );
}

