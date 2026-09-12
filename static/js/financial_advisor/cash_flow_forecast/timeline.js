"use strict";
// Cash flow forecast tab — month-by-month timeline HTML fragment builder.
// Split from cash_flow.js. This file is part of the financial_advisor module.
// Siblings: states.js (loading/error/cards/warnings), cash_flow.js (composition + load).

function _buildCashFlowTimelineHtml(timeline) {
  const langCode = currentLang ? currentLang() : document.documentElement.lang || "en";
  const monthFmt = new Intl.DateTimeFormat(langCode, { month: "long", year: "numeric" });

  const timelineHtml = `
    <div class="card border-0 mb-3" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:8px; overflow:hidden;">
      ${timeline
        .map((month, index) => {
          const monthDate = `${month.month || ""}-01`;
          const monthLabel = month.month ? monthFmt.format(new Date(monthDate)) : "";

          const hasCertificateMaturity = (month.events || []).some(
            (e) => e.type === "certificate_maturity"
          );
          const maturityBadgeHtml = hasCertificateMaturity
            ? `
          <span style="background:rgba(0, 168, 107, 0.15); color:#00e676; padding:2px 8px; border-radius:12px; font-size:11px; margin-left:8px; font-weight:600;" data-i18n="cash_flow_event_certificate_maturity"></span>
        `
            : "";

          const eventsHtml = (month.events || [])
            .map((event) => {
              const isPositive = Number(event.amount || 0) >= 0;
              const sign = isPositive ? "+" : "-";
              const amountText = _money(Math.abs(Number(event.amount || 0)));
              return `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-color);">
              <span style="color:var(--text-primary);" data-i18n="${_eventTranslationKey(event.type)}"></span>
              <span style="color:var(--text-secondary); font-weight:600;">${sign}${amountText}</span>
            </div>
          `;
            })
            .join("");

          const displayStyle = index < 3 ? "block" : "none";
          const isHiddenClass = index >= 3 ? "hidden-month-card" : "";
          let borderBottom = "1px solid var(--border-color)";
          if (index === timeline.length - 1 || (index === 2 && timeline.length > 3)) {
            borderBottom = "none";
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
        })
        .join("")}
    </div>
  `;

  const showAllBtnHtml =
    timeline.length > 3
      ? `
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
  `
      : "";

  return timelineHtml + showAllBtnHtml;
}
