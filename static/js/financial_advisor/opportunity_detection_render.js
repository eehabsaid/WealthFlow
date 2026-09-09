"use strict";
// Opportunity detection tab — main render orchestrator and data loader.
// Split into sibling files (200-line backlog):
// opportunity_detection_helpers.js, opportunity_detection_card.js. This
// file assembles the style block, hero header, and card grid (using
// buildOpportunityCardHtml per item instead of the original inline
// forEach + html += accumulation).
// ════════════════════════════════════════════════════════════════════════════

function _renderOpportunityDetection(payload) {
  const pane = document.getElementById("fa-pane-opportunity-detection");
  if (!pane) return;

  const count = Number(payload?.count || 0);
  const opportunities = payload?.opportunities || [];

  let html = `
    <style>
      .opp-card-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 24px;
      }
      @media (min-width: 1000px) {
        .opp-card-grid {
          grid-template-columns: repeat(2, 1fr);
        }
      }
      .opp-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 24px;
        display: flex;
        flex-direction: column;
        height: 100%;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
      }
      .opp-card:hover {
        transform: translateY(-2px);
        border-color: var(--accent-primary);
      }
      .opp-badge {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border-radius: 12px;
        padding: 3px 12px;
        display: inline-block;
      }
      .opp-badge-high {
        background: rgba(255, 59, 48, 0.15);
        color: var(--accent-red);
      }
      .opp-badge-medium {
        background: rgba(255, 149, 0, 0.15);
        color: var(--accent-yellow);
      }
      .opp-badge-low {
        background: rgba(52, 199, 89, 0.15);
        color: var(--accent-green);
      }
      .opp-badge-info {
        background: rgba(14, 165, 233, 0.15);
        color: var(--accent-primary);
      }
      .opp-signals-box {
        background: var(--bg-tertiary);
        border-radius: 8px;
        padding: 16px 20px;
        margin: 20px 0;
      }
      .opp-signals-table {
        width: 100%;
        font-size: 13px;
        border-collapse: collapse;
      }
      .opp-signals-table td {
        padding: 6px 0;
      }
      .opp-signal-label {
        color: var(--text-secondary);
        font-weight: 500;
      }
      .opp-signal-val {
        color: var(--text-primary);
        font-weight: 700;
        text-align: right;
      }
      [dir="rtl"] .opp-signal-val {
        text-align: left;
      }
      .opp-highlighted-amount {
        font-size: 32px;
        font-weight: 800;
        color: var(--accent-primary);
        letter-spacing: -0.5px;
        margin: 8px 0 20px 0;
        line-height: 1.2;
      }
      .opp-action-box {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px 20px;
        font-size: 13px;
        line-height: 1.6;
        color: var(--text-primary);
        margin-top: auto;
      }
    </style>

    <!-- Hero Header Card -->
    <div class="card border-0 mb-4 fade-in-up" style="background:var(--bg-secondary); border:1px solid var(--border-color) !important; border-radius:12px;">
      <div class="card-body" style="padding:32px; text-align:center;">
        <div style="font-size:48px; font-weight:800; color:var(--accent-primary); line-height:1; margin-bottom:10px;">${count}</div>
        <div style="font-size:12px; font-weight:700; color:var(--text-secondary); letter-spacing:1px; text-transform:uppercase;" data-i18n="opportunities_found_label"></div>
      </div>
    </div>

    <!-- Section Title -->
    <h5 style="color:var(--text-primary); font-weight:700; margin-bottom:20px; font-size:1.15rem;" data-i18n="opportunities_list_title"></h5>
  `;

  if (opportunities.length === 0) {
    html += `
      <div class="card border-0 fade-in-up" style="background:var(--bg-secondary); border:1px solid var(--border-color) !important; border-radius:12px; padding:48px 24px; text-align:center;">
        <i class="bi bi-check-circle-fill" style="font-size:48px; color:var(--accent-green); margin-bottom:16px;"></i>
        <h5 style="color:var(--text-primary); font-weight:700; margin-bottom:8px;" data-i18n="opportunities_empty_state"></h5>
      </div>
    `;
  } else {
    html += `<div class="opp-card-grid">`;
    opportunities.forEach((item) => {
      html += buildOpportunityCardHtml(item);
    });
    html += `</div>`;
  }

  pane.innerHTML = html;
  if (typeof applyTranslations === "function") applyTranslations();
}

async function loadOpportunityDetection(force = false) {
  if (_opportunityDetectionData && !force) {
    _renderOpportunityDetection(_opportunityDetectionData);
    _opportunityDetectionLoaded = true;
    return;
  }

  _renderOpportunityDetectionLoading();
  try {
    const response = await fetch("/api/financial-advisor/opportunity-detection/");
    if (!response.ok) {
      throw new Error("opportunity_detection_fetch_failed");
    }
    const payload = await response.json();
    _opportunityDetectionData = payload;
    _renderOpportunityDetection(payload);
    _opportunityDetectionLoaded = true;
  } catch (error) {
    _renderOpportunityDetectionError();
  }
}

window.loadOpportunityDetection = loadOpportunityDetection;
