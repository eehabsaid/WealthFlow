// balance.js — balance page
async function renderBalance() {
    const mc = document.getElementById("main-content");
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const [bRes, bankRes, currRes, ratesRes, goldRes, forecastRes] = await Promise.all([
        fetch("/api/balance/"),
        fetch("/api/banks/"),
        fetch("/api/currencies/"),
        fetch("/api/rates/"),
        fetch("/api/gold/"),
        fetch("/api/certificate-forecast/"),
    ]);

    const bData = await bRes.json();
    const bankData = await bankRes.json();
    const currData = await currRes.json();
    const ratesData = await ratesRes.json();
    const goldData = await goldRes.json();
    const forecastData = await forecastRes.json();
    const entries = bData.entries;
    _banks = bankData.banks;
    _currencies = currData.currencies || [];

    const totals = {};
    _currencies.forEach((c) => { totals[c.code] = 0; });
    entries.forEach((e) => {
        if (totals[e.currency_code] !== undefined) { totals[e.currency_code] += e.amount; }
    });

    const totalEGP = totals.EGP || 0;

    const getRate = (code) => {
        const rate = (ratesData.rates || []).find((r) => r.currency_code === code);
        return rate ? Number(rate.buy_rate) : 0;
    };

    const usdAmount = totals["USD"] || 0;
    const eurAmount = totals["EUR"] || 0;
    const sarAmount = totals["SAR"] || 0;
    const goldGrams = totals["Gold"] || 0;

    const usdRate = getRate("USD");
    const eurRate = getRate("EUR");
    const sarRate = getRate("SAR");

    const gold24kSell = goldData.gold ? Number(goldData.gold.carat_24k) : 0;
    const goldValue = goldGrams > 0 ? goldGrams * (gold24kSell + 28.5) : 0;

    const grandTotal = totalEGP + usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate + goldValue;

    const currencyCards = _currencies
        .map((cur) => `<div class="col-6 col-md-4 col-lg-2"><div class="currency-card"><div class="cur-flag">${cur.flag || "💱"}</div><div class="cur-code" data-i18n="${cur.code}">${cur.code}</div><div class="cur-amount num-fmt" data-value="${totals[cur.code] || 0}">${fmt(totals[cur.code] || 0)}</div></div></div>`)
        .join("");

    const bankMap = {};
    _banks.forEach((b) => { bankMap[b.id] = b.name; });

    const rows = entries
    .map(
        (e) => `
        <tr>
            <td data-i18n-key="${e.title || ""}">${_t && _t[e.title] ? _t[e.title] : (e.title || "")}</td>
            <td data-i18n-prefix="type_" data-i18n-value="${e.balance_type || ""}">${_t && _t["type_" + e.balance_type] ? _t["type_" + e.balance_type] : (e.balance_type || "")}</td>
            <td data-i18n-prefix="bank_" data-i18n-value="${e.bank_name || ""}">${e.bank_name || "_"}</td>
            <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${e.currency_flag} ${e.currency_code}</span></td>
            <td class="text-end amt-positive num-fmt" data-value="${e.amount}">${fmt(e.amount)}</td>
            <td>
                <button class="btn-icon" onclick="showBalanceModal(${e.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBalanceEntry(${e.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
        )
        .join("");

    mc.innerHTML = `
        <div class="page-header"><div><div class="page-title" data-i18n="nav_balance">Balance</div></div></div>
        <div class="row g-3 mb-4">${currencyCards}</div>
        <div class="kpi-card mb-4" style="text-align:center">
            <div class="kpi-label" data-i18n="grand_total">Total All Balances (EGP equiv.)</div>
            <div class="kpi-value num-fmtpresent" style="color:var(--accent-green);font-size:32px" data-value="${grandTotal}">${fmtpresent(grandTotal)} <span data-i18n="EGP">EGP</span></div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px" data-i18n="balance_formula_desc">= EGP + (USD × rate) + (EUR × rate) + (SAR × rate) + (Gold × 24K sell price + 28.5)</div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
                <span class="num-fmt" data-value="${totalEGP}">${fmt(totalEGP)}</span> + 
                (<span class="num-fmt" data-value="${usdAmount}">${fmt(usdAmount)}</span> * <span class="num-fmt" data-value="${usdRate}">${fmt(usdRate)}</span>) + 
                (<span class="num-fmt" data-value="${eurAmount}">${fmt(eurAmount)}</span> * <span class="num-fmt" data-value="${eurRate}">${fmt(eurRate)}</span>) + 
                (<span class="num-fmt" data-value="${sarAmount}">${fmt(sarAmount)}</span> * <span class="num-fmt" data-value="${sarRate}">${fmt(sarRate)}</span>) + 
                ((<span class="num-fmt" data-value="${goldGrams}">${fmt(goldGrams)}</span> * (<span class="num-fmt" data-value="${gold24kSell}">${fmt(gold24kSell)}</span> + 28.5))
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
                <span class="num-fmt" data-value="${totalEGP}">${fmt(totalEGP)}</span> + 
                (<span class="num-fmt" data-value="${usdAmount * usdRate}">${fmt(usdAmount * usdRate)}</span>) + 
                (<span class="num-fmt" data-value="${eurAmount * eurRate}">${fmt(eurAmount * eurRate)}</span>) + 
                (<span class="num-fmt" data-value="${sarAmount * sarRate}">${fmt(sarAmount * sarRate)}</span>) + 
                (<span class="num-fmt" data-value="${goldValue}">${fmt(goldValue)}</span>)
            </div>
        </div>
        
        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="financial_intelligence">Financial Intelligence</div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:20px;">
                <div><div class="kpi-label" data-i18n="net_worth">Net Worth</div><div class="kpi-value num-fmtpresent" data-value="${grandTotal}">${fmtpresent(grandTotal)}</div></div>
                <div><div class="kpi-label" data-i18n="liquid_cash">Liquid Cash</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="certificate_investments">Certificate Investments</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.certificate_balance || 0}">${fmtpresent(forecastData.certificate_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="foreign_currency_value">Foreign Currency Value</div><div class="kpi-value num-fmtpresent" data-value="${usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate}">${fmtpresent(usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate)}</div></div>
                <div><div class="kpi-label" data-i18n="gold_value">Gold Value</div><div class="kpi-value num-fmtpresent" data-value="${goldValue}">${fmtpresent(goldValue)}</div></div>
                <div><div class="kpi-label" data-i18n="monthly_salary">Monthly Salary</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.monthly_salary || 0}">${fmtpresent(forecastData.monthly_salary || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="certificate_income">Certificate Income</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.monthly_certificate_income || 0}">${fmtpresent(forecastData.monthly_certificate_income || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="income_dependency">Income Dependency</div><div class="kpi-value"><span class="num-fmtint" data-value="${forecastData.certificate_income_ratio || 0}">${fmtInt(forecastData.certificate_income_ratio || 0)}</span>%</div></div>
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="certificate_forecast">Certificate Forecast</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:20px;">
                <div><div class="kpi-label" data-i18n="next_30_days">Next 30 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_30 || 0}">${fmtpresent(forecastData.forecast_30 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="next_90_days">Next 90 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_90 || 0}">${fmtpresent(forecastData.forecast_90 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="next_180_days">Next 180 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_180 || 0}">${fmtpresent(forecastData.forecast_180 || 0)}</div></div>
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="future_cash_position">Future Cash Position</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:20px;">
                <div><div class="kpi-label" data-i18n="current_cash">Current Cash</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_30_days">Cash After 30 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_30 || 0}">${fmtpresent(forecastData.future_cash_30 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_90_days">Cash After 90 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_90 || 0}">${fmtpresent(forecastData.future_cash_90 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_180_days">Cash After 180 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_180 || 0}">${fmtpresent(forecastData.future_cash_180 || 0)}</div></div>
            </div>
        </div>

       <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="investment_recommendations">Investment Recommendations</div>
            <div style="margin-top:15px">
                ${(forecastData.investment_recommendations || []).map((r) => `<div data-i18n-key="${r}" style="padding:10px; margin-bottom:8px; border-radius:8px; background:var(--bg-secondary); border:1px solid var(--border-color);">${_t && _t[r] ? _t[r] : r}</div>`).join("")}
            </div>
        </div>

        <div class="kpi-card mb-4">
        <div class="kpi-label" data-i18n="recommended_action">Recommended Action</div>
            <div
                data-i18n-key="${forecastData.action_plan?.key || ''}"
                data-gold-amount="${forecastData.action_plan?.gold_amount || 0}"
                data-cash-amount="${forecastData.action_plan?.cash_amount || 0}"
                data-certificate-amount="${forecastData.action_plan?.certificate_amount || 0}"
                style="margin-top:15px;font-weight:600;"
            >
                ${
                    forecastData.action_plan?.key
                        ? (_t[forecastData.action_plan.key] || forecastData.action_plan.key)
                            .replace("{gold_amount}", fmtpresent(forecastData.action_plan.gold_amount || 0))
                            .replace("{cash_amount}", fmtpresent(forecastData.action_plan.cash_amount || 0))
                            .replace("{certificate_amount}", fmtpresent(forecastData.action_plan.certificate_amount || 0))
                        : ""
                }
            </div>
        </div>
        </div>

        ${forecastData.upcoming?.length ? `
            <div class="kpi-label" data-i18n="upcoming_certificate_maturities" style="margin-top: 24px; font-weight: 600;">Upcoming Certificate Maturities</div>
            <div class="table-container" style="margin-top:15px; margin-bottom: 24px;">
                <table class="data-table">
                    <thead><tr><th data-i18n="bank_name">Bank</th><th data-i18n="expiry_date">Expiry Date</th><th data-i18n="days_left">Days Left</th><th data-i18n="certificate_value">Value</th></tr></thead>
                    <tbody>
                        ${forecastData.upcoming.map((c) => `<tr><td>${c.bank}</td><td class="local-date-field" data-expiry="${c.expiry_date}"></td><td><span style="color:${c.days_left <= 30 ? "var(--accent-red)" : c.days_left <= 90 ? "orange" : "var(--text-primary)"}; font-weight:600;">${c.days_left}</span></td><td class="num-fmtpresent" data-value="${c.amount}">${fmtpresent(c.amount)}</td></tr>`).join("")}
                    </tbody>
                </table>
            </div>` : ""
        }

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="asset_allocation">Asset Allocation</div>
            ${renderAllocationBar("cash", forecastData.cash_balance || 0, grandTotal)}
            ${renderAllocationBar("foreignCurrency", usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate, grandTotal)}
            ${renderAllocationBar("certificates",forecastData.certificate_balance || 0,grandTotal)}
            ${renderAllocationBar("gold", goldValue, grandTotal)}
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="financial_recommendations">Financial Recommendations</div>
            <div style="margin-top:15px">
                ${(forecastData.financial_recommendations || []).map((r) => `<div data-i18n-key="${r}" style="padding:12px; margin-bottom:10px; background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:10px;">${_t && _t[r] ? _t[r] : r}</div>`).join("")}
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible"><div class="table-container"><table class="data-table"><thead><tr><th data-i18n="balance_title">Title</th><th data-i18n="balance_type">Balance Type</th><th data-i18n="balance_bank">Bank</th><th data-i18n="balance_currency">Currency</th><th class="text-end" data-i18n="balance_amount">Amount</th><th data-i18n="actions">Actions</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;

    applyTranslations();
}

async function showBalanceModal(entryId) {
    let entry = null;
    if (entryId) {
        const res = await fetch("/api/balance/");
        const data = await res.json();
        entry = data.entries.find((e) => e.id === entryId);
    }
    const bankOpts = _banks.map((b) => `<option value="${b.id}" ${entry && entry.bank_id === b.id ? "selected" : ""}>${b.name}</option>`).join("");
    const curOpts = _currencies.map((c) => `<option value="${c.id}" ${entry && entry.currency_id === c.id ? "selected" : ""}>${c.flag} ${c.code} - ${c.name}</option>`).join("");

    const typeOpts = `
        <option value="cash" data-i18n="type_cash" ${entry && entry.balance_type === "cash" ? "selected" : ""}>💵 Cash</option>
        <option value="bank" data-i18n="type_bank" ${entry && entry.balance_type === "bank" ? "selected" : ""}>🏦 Bank Account</option>
        <option value="certificate" data-i18n="type_certificate" ${entry && entry.balance_type === "certificate" ? "selected" : ""}>📜 Certificate</option>
    `;

    const html = `
        <div class="modal-header"><h5 class="modal-title" data-i18n="${entry ? "title_edit_balance" : "title_add_balance"}">${entry ? "Edit Balance Entry" : "Add Balance Entry"}</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12"><label data-i18n="balance_title">Title</label><input type="text" class="form-control" id="bTitle" value="${entry ? entry.title : ""}"></div>
                <div class="col-12"><label data-i18n="balance_type">Balance Type</label><select class="form-select" id="bbalance_type"><option value="" data-i18n="select_type">— Select Type —</option>${typeOpts}</select></div>
                <div class="col-6"><label data-i18n="balance_bank">Bank</label><select class="form-select" id="bBank"><option value="" data-i18n="none_option">— None —</option>${bankOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_currency">Currency</label><select class="form-select" id="bCurrency">${curOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_amount">Amount</label><input type="number" step="0.01" class="form-control" id="bAmount" value="${entry ? entry.amount : ""}"></div>
                <div class="col-12"><label data-i18n="notes">Notes</label><input type="text" class="form-control" id="bNotes" value="${entry ? entry.notes : ""}"></div>
            </div>
        </div>
        <div class="modal-footer"><button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">Cancel</button><button class="btn-primary-custom" onclick="saveBalanceEntry(${entryId})" data-i18n="btn_save">Save</button></div>`;

    showModal(html);
    applyTranslations();
}

async function saveBalanceEntry(entryId) {
    const bankVal = document.getElementById("bBank").value;
    const typeVal = document.getElementById("bbalance_type").value;

    const body = {
        title: document.getElementById("bTitle").value,
        balance_type: typeVal || null,
        bank_id: bankVal ? parseInt(bankVal) : null,
        currency_id: parseInt(document.getElementById("bCurrency").value) || 1,
        amount: parseFloat(document.getElementById("bAmount").value) || 0,
        notes: document.getElementById("bNotes").value,
    };

    const url = entryId ? `/api/balance/${entryId}/` : "/api/balance/";
    const method = entryId ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

    if (res.ok) {
        closeModal();
        showToast("Saved ✓");
        renderBalance();
    } else {
        showToast("Error saving", "error");
    }
}

async function deleteBalanceEntry(entryId) {
    if (!confirm("Delete this entry?")) return;
    const res = await fetch(`/api/balance/${entryId}/`, { method: "DELETE" });
    if (res.ok) {
        showToast("Deleted");
        renderBalance();
    }
}

function renderAllocationBar(labelKey, value, total) {
    const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
    return `<div style="margin-top:14px"><div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;"><span data-i18n="${labelKey}">${labelKey}</span><span>${pct}%</span></div><div style="height:12px;background:var(--bg-tertiary);border-radius:999px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:var(--accent-primary);"></div></div></div>`;
}