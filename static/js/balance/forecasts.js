'use strict';

// balance/forecasts.js — Forecasts tab renderer
// Renders: Certificate Forecast + Future Cash Position + Upcoming Certificate Maturities
// Called by index.js with pre-fetched data. Zero API calls here.
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceForecasts(data) {
    const pane = document.getElementById('bal-pane-forecasts');
    if (!pane) return;

    const { forecastData } = data;

    pane.innerHTML = `
        <div class="row g-3 mb-4">
            <div class="col-12 col-xl-6">
                <div class="kpi-card h-100 fi-forecast-card">
                    <div class="kpi-label" data-i18n="certificate_forecast">Certificate Forecast</div>
                    <div class="fi-amount-grid fi-amount-grid-3">
                        <div class="fi-amount-tile ${Number(forecastData.forecast_30 || 0) > 0 ? 'fi-up' : ''}">
                            <div class="fi-amount-caption" data-i18n="next_30_days">Next 30 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_30 || 0}">${fmtpresent(forecastData.forecast_30 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                        <div class="fi-amount-tile ${Number(forecastData.forecast_90 || 0) > 0 ? 'fi-up' : ''}">
                            <div class="fi-amount-caption" data-i18n="next_90_days">Next 90 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_90 || 0}">${fmtpresent(forecastData.forecast_90 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                        <div class="fi-amount-tile ${Number(forecastData.forecast_180 || 0) > 0 ? 'fi-up' : ''}">
                            <div class="fi-amount-caption" data-i18n="next_180_days">Next 180 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_180 || 0}">${fmtpresent(forecastData.forecast_180 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-xl-6">
                <div class="kpi-card h-100 fi-cash-position-card">
                    <div class="kpi-label" data-i18n="future_cash_position">Future Cash Position</div>
                    <div class="fi-amount-grid fi-amount-grid-4">
                        <div class="fi-amount-tile">
                            <div class="fi-amount-caption" data-i18n="current_cash">Current Cash</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                        <div class="fi-amount-tile">
                            <div class="fi-amount-caption" data-i18n="cash_after_30_days">Cash After 30 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_30 || 0}">${fmtpresent(forecastData.future_cash_30 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                        <div class="fi-amount-tile">
                            <div class="fi-amount-caption" data-i18n="cash_after_90_days">Cash After 90 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_90 || 0}">${fmtpresent(forecastData.future_cash_90 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                        <div class="fi-amount-tile">
                            <div class="fi-amount-caption" data-i18n="cash_after_180_days">Cash After 180 Days</div>
                            <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_180 || 0}">${fmtpresent(forecastData.future_cash_180 || 0)}</div>
                            <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        ${forecastData.upcoming?.length ? `
            <div class="kpi-label" data-i18n="upcoming_certificate_maturities" style="margin-bottom:12px;font-weight:600;">${t('upcoming_certificate_maturities', 'Upcoming Certificate Maturities')}</div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="bank_name">Bank</th>
                            <th data-i18n="expiry_date">Expiry Date</th>
                            <th data-i18n="days_left">Days Left</th>
                            <th data-i18n="certificate_value">Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${forecastData.upcoming.map((c) => `
                            <tr>
                                <td>${c.bank}</td>
                                <td class="local-date-field" data-expiry="${c.expiry_date}"></td>
                                <td>
                                    <span style="color:${c.days_left <= 30 ? 'var(--accent-red)' : c.days_left <= 90 ? 'orange' : 'var(--text-primary)'};font-weight:600;">
                                        ${c.days_left}
                                    </span>
                                </td>
                                <td class="num-fmtpresent" data-value="${c.amount}">${fmtpresent(c.amount)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>` : ''}
    `;
}
