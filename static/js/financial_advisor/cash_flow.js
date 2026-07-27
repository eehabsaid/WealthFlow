"use strict";
// Cash flow forecast tab rendering and load handlers
// This file is part of the financial_advisor module. Do not edit directly.

function _renderCashFlowLoading() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="cash_flow_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderCashFlowError() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="cash_flow_error"></span>
    </div>
  `;
  applyTranslations();
}

function _renderCashFlowForecast(payload) {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  const cp = payload?.checkpoints || {};
  const timeline = payload?.timeline || [];
  const summary = payload?.summary || {};
  const warnings = payload?.warnings || [];

  const cards = [
    { key: "cash_flow_card_current", value: cp.current || 0 },
    { key: "cash_flow_card_next_month", value: cp.next_month || 0 },
    { key: "cash_flow_card_month_3", value: cp.month_3 || 0 },
    { key: "cash_flow_card_month_6", value: cp.month_6 || 0 },
    { key: "cash_flow_card_month_12", value: cp.month_12 || 0 },
  ];

  const cardsHtml = cards.map((card) => `
    <div class="col-12 col-sm-6 col-xl">
      <div class="asset-summary-card h-100" style="background:var(--bg-secondary);">
        <div class="asset-summary-label" data-i18n="${card.key}"></div>
        <div class="asset-summary-value">${_money(card.value)}</div>
      </div>
    </div>
  `).join("");

  const warningHtml = warnings.map((warning) => `
    <div class="alert alert-${warning.level || "secondary"}" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary); margin-bottom:10px;">
      <span data-i18n="${warning.key}"></span>
    </div>
  `).join("");

  const langCode = currentLang ? currentLang() : (document.documentElement.lang || "en");
  const monthFmt = new Intl.DateTimeFormat(langCode, { month: "long", year: "numeric" });

  const timelineHtml = `
    <div class="card border-0 mb-3" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; overflow:hidden;">
      ${timeline.map((month, index) => {
        const monthDate = `${month.month || ""}-01`;
        const monthLabel = month.month ? monthFmt.format(new Date(monthDate)) : "";
        
        const hasCertificateMaturity = (month.events || []).some(e => e.type === 'certificate_maturity');
        const maturityBadgeHtml = hasCertificateMaturity ? `
          <span style="background:rgba(0, 168, 107, 0.15); color:#00e676; padding:2px 8px; border-radius:12px; font-size:11px; margin-left:8px; font-weight:600;" data-i18n="cash_flow_event_certificate_maturity"></span>
        ` : '';

        const eventsHtml = (month.events || []).map((event) => {
          const isPositive = Number(event.amount || 0) >= 0;
          const sign = isPositive ? "+" : "-";
          const amountText = _money(Math.abs(Number(event.amount || 0)));
          return `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-color);">
              <span style="color:var(--text-primary);" data-i18n="${_eventTranslationKey(event.type)}"></span>
              <span style="color:var(--text-secondary); font-weight:600;">${sign}${amountText}</span>
            </div>
          `;
        }).join("");

        const displayStyle = index < 3 ? 'block' : 'none';
        const isHiddenClass = index >= 3 ? 'hidden-month-card' : '';
        let borderBottom = '1px solid var(--border-color)';
        if (index === timeline.length - 1 || (index === 2 && timeline.length > 3)) {
            borderBottom = 'none';
        }

        return `
          <div class="${isHiddenClass} month-card-row" style="display: ${displayStyle}; border-bottom: ${borderBottom};">
            <div style="padding:16px; background:transparent; cursor:pointer; display:flex; justify-content:space-between; align-items:center;" onclick="
              const body = this.nextElementSibling;
              const isCollapsed = body.style.display === 'none';
              body.style.display = isCollapsed ? 'block' : 'none';
              this.querySelector('.toggle-icon').style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
            ">
              <div style="display:flex; align-items:center;">
                <span style="color:var(--text-primary); font-weight:700;">${monthLabel}</span>
                ${maturityBadgeHtml}
              </div>
              <div style="color:var(--text-secondary); font-size:12px; display:flex; align-items:center; gap:8px;">
                <span>${_money(month.ending_cash || 0)}</span>
                <svg class="toggle-icon" style="transition: transform 0.2s; fill:currentColor; width:16px; height:16px;" viewBox="0 0 16 16">
                  <path d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                </svg>
              </div>
            </div>
            <div style="display:none; padding:0 16px 16px 16px;">
              <div style="border-top:1px solid var(--border-color); padding-top:10px;">
                ${eventsHtml || `<div style="color:var(--text-secondary);" data-i18n="cash_flow_no_events"></div>`}
              </div>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;

  const showAllBtnHtml = timeline.length > 3 ? `
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; cursor:pointer;" onclick="
      const container = this.closest('#cash_flow_timeline_container');
      const hiddenCards = container.querySelectorAll('.hidden-month-card');
      const isShowingAll = this.getAttribute('data-showing') === 'true';
      hiddenCards.forEach(c => c.style.display = isShowingAll ? 'none' : 'block');
      this.setAttribute('data-showing', !isShowingAll);
      
      const rows = container.querySelectorAll('.month-card-row');
      if (rows.length > 3) {
         rows[2].style.borderBottom = isShowingAll ? 'none' : '1px solid var(--border-color)';
      }
      
      const span = this.querySelector('span');
      if (isShowingAll) {
          span.setAttribute('data-i18n-key', 'cash_flow_show_all_months');
          span.setAttribute('data-i18n-params', JSON.stringify({ count: ${timeline.length} }));
      } else {
          span.setAttribute('data-i18n-key', 'cash_flow_show_less');
          span.removeAttribute('data-i18n-params');
      }
      if (typeof applyTranslations === 'function') applyTranslations();
    ">
      <div class="card-body text-center" style="padding:12px;">
        <span style="color:var(--bs-primary, #0d6efd); font-weight:600; font-size:14px;" data-i18n-key="cash_flow_show_all_months" data-i18n-params='{"count": ${timeline.length}}'></span>
      </div>
    </div>
  ` : '';

  const largestEvent = summary.largest_cash_event || {};
  const largestExpense = summary.largest_planned_expense || {};
  const nearestMaturity = summary.nearest_certificate_maturity || {};

  pane.innerHTML = `
    <div class="row g-3 mb-4">
      ${cardsHtml}
    </div>

    <div class="mb-4">
      ${warningHtml}
    </div>

    <div class="mb-4" id="cash_flow_timeline_container">
      <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_timeline_title"></div>
      ${timelineHtml}
      ${showAllBtnHtml}
    </div>

    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_summary_title"></div>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_increase"></div>
              <div class="asset-summary-value">${_money(summary.expected_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_decrease"></div>
              <div class="asset-summary-value">${_money(summary.expected_decrease || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_net_change"></div>
              <div class="asset-summary-value">${_money(summary.net_cash_change || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_cash_event"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestEvent.type)}"></div>
              <div class="asset-summary-value">${_money(Math.abs(largestEvent.amount || 0))}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_nearest_maturity"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;">${formatDate(nearestMaturity.date) || "-"}</div>
              <div class="asset-summary-value">${_money(nearestMaturity.amount || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_planned_expense"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestExpense.type)}"></div>
              <div class="asset-summary-value">${_money(largestExpense.amount || 0)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  applyTranslations();
}

async function loadCashFlowForecast(force = false) {
  if (_cashFlowForecastData && !force) {
    _renderCashFlowForecast(_cashFlowForecastData);
    _cashFlowForecastLoaded = true;
    return;
  }

  _renderCashFlowLoading();
  try {
    const response = await fetch("/api/financial-advisor/cash-flow-forecast/");
    if (!response.ok) {
      throw new Error("cash_flow_fetch_failed");
    }
    const payload = await response.json();
    _cashFlowForecastData = payload;
    _renderCashFlowForecast(payload);
    _cashFlowForecastLoaded = true;
  } catch (error) {
    _renderCashFlowError();
  }
}

