'use strict';

async function _getCertStatusOptions(currentStatus) {
    try {
        const res = await fetch('/api/cert-statuses/');
        const data = await res.json();
        const statuses = data.statuses || [];
        
        if (statuses.length === 0) {
            const defaultStatuses = ['Active', 'Maturing', 'Renewed', 'Closed'];
            return defaultStatuses
                .map((s) => `<option value="${s}" ${s === (currentStatus || 'Active') ? 'selected' : ''}>${s}</option>`)
                .join('');
        } else {
            return statuses
                .map(
                    (s) => `<option value="${s.name}" ${s.name === (currentStatus || '') || (!currentStatus && s.is_default) ? 'selected' : ''}>${s.name}</option>`
                )
                .join('');
        }
    } catch (e) {
        // Fallback if API fails
        const defaultStatuses = ['Active', 'Maturing', 'Renewed', 'Closed'];
        return defaultStatuses
            .map((s) => `<option value="${s}" ${s === (currentStatus || 'Active') ? 'selected' : ''}>${s}</option>`)
            .join('');
    }
}

function parseNumberInput(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const raw = el.value || '';
    const normalized = String(raw).replace(/,/g, '').trim();
    if (normalized === '') return null;
    const num = Number(normalized);
    return Number.isFinite(num) ? num : null;
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & DELETE
// ════════════════════════════════════════════════════════════════════════════

function formatCertificateHistoryDate(value) {
    if (!value) return '—';
    const res = formatDate(value);
    return res || value;
}

function formatCertificateFrequencyLabel(value) {
    const freq = String(value || '').trim().toLowerCase();
    if (freq === 'monthly') return t('freq_monthly', 'Monthly');
    if (freq === 'quarterly') return t('freq_quarterly', 'Quarterly');
    if (freq === 'semi_annually' || freq === 'semi-annually' || freq === 'semi annually' || freq === 'semiannual') return t('freq_semi_annually', 'Semi-Annually');
    if (freq === 'annually' || freq === 'annual' || freq === 'yearly') return t('freq_annually', 'Annually');
    if (freq === 'at_maturity') return t('freq_at_maturity', 'At Maturity');
    return value || '—';
}

function formatCertificateHistoryDateFromDate(dateObj) {
    if (!(dateObj instanceof Date) || Number.isNaN(dateObj.getTime())) return '—';
    const res = formatDate(dateObj);
    return res || '—';
}