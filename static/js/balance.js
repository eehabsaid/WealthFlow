// balance.js — balance page
async function renderBalance() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const [bRes, bankRes, currRes, ratesRes, goldRes] = await Promise.all([
        fetch('/api/balance/'),
        fetch('/api/banks/'),
        fetch('/api/currencies/'),
        fetch('/api/rates/'),
        fetch('/api/gold/'),
    ]);

    const bData = await bRes.json();
    const bankData = await bankRes.json();
    const currData = await currRes.json();
    const ratesData = await ratesRes.json();
    const goldData = await goldRes.json();
    const entries = bData.entries;
    _banks = bankData.banks;
    _currencies = currData.currencies || [];

    const totals = {};
    _currencies.forEach(c => { totals[c.code] = 0; });
    entries.forEach(e => { if (totals[e.currency_code] !== undefined) totals[e.currency_code] += e.amount; });
    
    const totalEGP = totals.EGP || 0;

    // Grand Total formula — matches Excel BALANCE tab exactly:
    // =TotalEGP + (USD * USDrate) + (EUR * EURrate) + (SAR * SARrate) + (Gold * (Gold21Ksell + 28.5))
    const getRate = (code) => {
        const rate = (ratesData.rates || []).find(r => r.currency_code === code);
        return rate ? Number(rate.buy_rate) : 0;
    };

    const usdAmount  = totals['USD']  || 0;
    const eurAmount  = totals['EUR']  || 0;
    const sarAmount  = totals['SAR']  || 0;
    const goldGrams  = totals['Gold'] || 0;

    const usdRate    = getRate('USD');   // EGP per 1 USD  (Exchange Rates B2)
    const eurRate    = getRate('EUR');   // EGP per 1 EUR  (Exchange Rates B3)
    const sarRate    = getRate('SAR');   // EGP per 1 SAR  (Exchange Rates B11)

    // Gold: use 24K sell price (Gold Price C3 = column C row 3) + 28.5 fixed offset  (per Excel formula)
    const gold24kSell = goldData.gold ? Number(goldData.gold.carat_24k) : 0;
    const goldValue   = goldGrams > 0 ? (goldGrams * (gold24kSell + 28.5)) : 0;

    const grandTotal = totalEGP
        + (usdAmount  * usdRate)
        + (eurAmount  * eurRate)
        + (sarAmount  * sarRate)
        + goldValue;

    const currencyCards = _currencies.map(cur => `
        <div class="col-6 col-md-4 col-lg-2">
            <div class="currency-card">
                <div class="cur-flag">${cur.flag || '💱'}</div>
                <div class="cur-code" data-i18n="${cur.code}">${cur.code}</div>
                <div class="cur-amount">${fmt(totals[cur.code] || 0)}</div>
            </div>
        </div>`).join('');

    const bankMap = {};
    _banks.forEach(b => { bankMap[b.id] = b.name; });

    const rows = entries.map(e => `
        <tr>
            <td>${e.title}</td>
            <td>${e.bank_name || '—'}</td>
            <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${e.currency_flag} ${e.currency_code}</span></td>
            <td class="text-end amt-positive">${fmt(e.amount)}</td>
            <td>
                <button class="btn-icon" onclick="showBalanceModal(${e.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBalanceEntry(${e.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_balance">Balance</div></div>
        </div>
        <div class="row g-3 mb-4">${currencyCards}</div>
        <div class="kpi-card mb-4" style="text-align:center">
            <div class="kpi-label" data-i18n="grand_total">Total All Balances (EGP equiv.)</div>
            <div class="kpi-value" style="color:var(--accent-green);font-size:32px">${fmtpresent(grandTotal)} <span data-i18n="EGP">EGP</span></div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
                = EGP + (USD × rate) + (EUR × rate) + (SAR × rate) + (Gold × 24K sell price + 28.5)
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
        
                ${fmt(totalEGP)} + (${fmt(usdAmount)}  * ${fmt(usdRate)}) + (${fmt(eurAmount)}  * ${fmt(eurRate)}) + (${fmt(sarAmount)}  * ${fmt(sarRate)}) + ((${fmt(goldGrams)} * (${fmt(gold24kSell)} + 28.5))
                
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
        
                ${fmt(totalEGP)} + (${fmt(usdAmount  * usdRate)}) + (${fmt(eurAmount  * eurRate)}) + (${fmt(sarAmount  * sarRate)}) + (${fmt(goldValue)})
            </div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="balance_title">Title</th>
                    <th data-i18n="balance_bank">Bank</th>
                    <th data-i18n="balance_currency">Currency</th>
                    <th class="text-end" data-i18n="balance_amount">Amount</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
    applyTranslations();
}

async function showBalanceModal(entryId) {
    let entry = null;
    if (entryId) {
        const res = await fetch('/api/balance/');
        const data = await res.json();
        entry = data.entries.find(e => e.id === entryId);
    }
    const bankOpts = _banks.map(b =>
        `<option value="${b.id}" ${entry && entry.bank_id === b.id ? 'selected':''}>${b.name}</option>`
    ).join('');
    const curOpts = _currencies.map(c =>
        `<option value="${c.id}" ${entry && entry.currency_id === c.id ? 'selected':''}>${c.flag} ${c.code} - ${c.name}</option>`
    ).join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title">${entry ? t('btn_edit','Edit') : t('btn_add','Add')} Balance Entry</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="balance_title">Title</label>
                    <input type="text" class="form-control" id="bTitle" value="${entry ? entry.title : ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="balance_bank">Bank</label>
                    <select class="form-select" id="bBank">
                        <option value="">— None —</option>${bankOpts}
                    </select>
                </div>
                <div class="col-3">
                    <label data-i18n="balance_currency">Currency</label>
                    <select class="form-select" id="bCurrency">${curOpts}</select>
                </div>
                <div class="col-3">
                    <label data-i18n="balance_amount">Amount</label>
                    <input type="number" step="0.01" class="form-control" id="bAmount" value="${entry ? entry.amount : ''}">
                </div>
                <div class="col-12">
                    <label data-i18n="notes">Notes</label>
                    <input type="text" class="form-control" id="bNotes" value="${entry ? entry.notes : ''}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBalanceEntry(${entryId})" data-i18n="btn_save">Save</button>
        </div>`;
    showModal(html);
    applyTranslations();
}

async function saveBalanceEntry(entryId) {
    const bankVal = document.getElementById('bBank').value;
    const body = {
        title: document.getElementById('bTitle').value,
        bank_id: bankVal ? parseInt(bankVal) : null,
        currency_id: parseInt(document.getElementById('bCurrency').value) || 1,
        amount: parseFloat(document.getElementById('bAmount').value) || 0,
        notes: document.getElementById('bNotes').value,
    };
    const url = entryId ? `/api/balance/${entryId}/` : '/api/balance/';
    const method = entryId ? 'PUT' : 'POST';
    const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    if (res.ok) { closeModal(); showToast('Saved ✓'); renderBalance(); }
    else showToast('Error saving', 'error');
}

async function deleteBalanceEntry(entryId) {
    if (!confirm('Delete this entry?')) return;
    const res = await fetch(`/api/balance/${entryId}/`, {method:'DELETE'});
    if (res.ok) { showToast('Deleted'); renderBalance(); }
}
