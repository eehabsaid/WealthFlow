// bank_certificates.js — Bank Certificates page
async function renderBankCertificates() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    await refreshBanks();
    const [cRes, certRes] = await Promise.all([
        fetch('/api/currencies/'),
        fetch('/api/bank-certificates/'),
    ]);

    const currData = await cRes.json();
    const certData = await certRes.json();
    const certificates = certData.certificates || [];
    _currencies = currData.currencies || [];

    const rows = certificates.map(c => `
        <tr>
            <td>${c.bank_name || '—'}</td>
            <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${c.currency_flag} ${c.currency_code || '—'}</span></td>
            <td>${c.issue_date || '—'}</td>
            <td>${c.expiry_date || '—'}</td>
            <td>${fmt(c.amount)}</td>
            <td>${c.interest_rate ? c.interest_rate : '—'}</td>
            <td>${c.interest_value ? fmt(c.interest_value) : '—'}</td>
            <td>${c.frequency || '—'}</td>
            <td>${c.status || '—'}</td>
            <td>
                <button class="btn-icon" onclick="showBankCertificateModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBankCertificate(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title">Bank Certificates</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                        <th>Bank</th>
                    <th>Currency</th>
                    <th>Issue Date</th>
                    <th>Expiry Date</th>
                    <th class="text-end">Amount</th>
                    <th>Interest Rate</th>
                    <th>Interest Value</th>
                    <th>Frequency</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
    applyTranslations();
}

async function showBankCertificateModal(certificateId) {
    let certificate = null;
    if (certificateId) {
        const res = await fetch(`/api/bank-certificates/${certificateId}/`);
        certificate = await res.json();
    }
    const bankOpts = _banks.map(b =>
        `<option value="${b.id}" ${certificate && certificate.bank_id === b.id ? 'selected' : ''}>${b.name}</option>`
    ).join('');
    const curOpts = _currencies.map(c =>
        `<option value="${c.id}" ${certificate && certificate.currency_id === c.id ? 'selected' : ''}>${c.flag} ${c.code}</option>`
    ).join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title">${certificate ? 'Edit' : 'Add'} Bank Certificate</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6"><label>Status</label><input class="form-control" id="bcStatus" value="${certificate ? certificate.status : 'Active'}"></div>
                <div class="col-6"><label>Bank</label><select class="form-select" id="bcBank"><option value="">— None —</option>${bankOpts}</select></div>
                <div class="col-6"><label>Currency</label><select class="form-select" id="bcCurrency"><option value="">— Select currency —</option>${curOpts}</select></div>
                <div class="col-6"><label>Issue Date</label><input type="date" class="form-control" id="bcIssue" value="${certificate ? certificate.issue_date : ''}"></div>
                <div class="col-6"><label>Expiry Date</label><input type="date" class="form-control" id="bcExpiry" value="${certificate ? certificate.expiry_date : ''}"></div>
                <div class="col-4"><label>Amount</label><input type="number" step="0.01" class="form-control" id="bcAmount" value="${certificate ? certificate.amount : ''}"></div>
                <div class="col-4"><label>Interest Rate</label><input type="number" step="0.0001" class="form-control" id="bcInterestRate" value="${certificate ? certificate.interest_rate : ''}"></div>
                <div class="col-4"><label>Interest Value</label><input type="number" step="0.01" class="form-control" id="bcInterestValue" value="${certificate ? certificate.interest_value : ''}"></div>
                <div class="col-6"><label>Frequency</label><input class="form-control" id="bcFrequency" value="${certificate ? certificate.frequency : ''}"></div>
                <div class="col-6"><label>Notes</label><textarea class="form-control" id="bcNotes" rows="2">${certificate ? certificate.notes : ''}</textarea></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBankCertificate(${certificateId})">Save</button>
        </div>`;
    showModal(html);
}

function parseNumberInput(id) {
    const raw = document.getElementById(id).value || '';
    const normalized = String(raw).replace(/,/g, '').trim();
    if (normalized === '') return null;
    const num = Number(normalized);
    return Number.isFinite(num) ? num : null;
}

async function saveBankCertificate(certificateId) {
    const amount = parseNumberInput('bcAmount');
    const interestRate = parseNumberInput('bcInterestRate');
    const interestValue = parseNumberInput('bcInterestValue');
    const body = {
        status: document.getElementById('bcStatus').value.trim(),
        bank_id: parseInt(document.getElementById('bcBank').value, 10) || null,
        currency_id: parseInt(document.getElementById('bcCurrency').value, 10) || null,
        issue_date: document.getElementById('bcIssue').value || null,
        expiry_date: document.getElementById('bcExpiry').value || null,
        amount: amount === null ? 0 : amount,
        interest_rate: interestRate === null ? 0 : interestRate,
        interest_value: interestValue === null ? 0 : interestValue,
        frequency: document.getElementById('bcFrequency').value.trim(),
        notes: document.getElementById('bcNotes').value.trim(),
    };

    const url = certificateId ? `/api/bank-certificates/${certificateId}/` : '/api/bank-certificates/';
    const method = certificateId ? 'PUT' : 'POST';
    const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    if (res.ok) {
        closeModal();
        showToast('Bank Certificate saved ✓');
        renderBankCertificates();
    } else {
        const text = await res.text();
        console.error('Bank certificate save failed', res.status, text);
        showToast('Error saving certificate: ' + (text || res.status), 'error');
    }
}

async function deleteBankCertificate(certificateId) {
    if (!confirm('Delete this certificate?')) return;
    const res = await fetch(`/api/bank-certificates/${certificateId}/`, {method:'DELETE'});
    if (res.ok) {
        showToast('Deleted');
        renderBankCertificates();
    } else {
        showToast('Error deleting certificate', 'error');
    }
}
