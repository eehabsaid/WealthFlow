'use strict';

function addMonthsKeepDay(baseDate, months) {
    const d = new Date(baseDate.getTime());
    const targetMonth = d.getMonth() + months;
    const targetYear = d.getFullYear() + Math.floor(targetMonth / 12);
    const month = ((targetMonth % 12) + 12) % 12;
    const day = d.getDate();
    const lastDay = new Date(targetYear, month + 1, 0).getDate();
    return new Date(targetYear, month, Math.min(day, lastDay));
}

function getCertificateNextPostingDate(certificate, items) {
    const status = String(certificate.status || '').trim().toLowerCase();
    if (status !== 'active') return '—';

    const issue = certificate.issue_date ? new Date(`${certificate.issue_date}T00:00:00`) : null;
    if (!issue || Number.isNaN(issue.getTime())) return '—';

    const frequency = String(certificate.frequency || '').trim().toLowerCase();
    const stepMonthsMap = {
        monthly: 1,
        quarterly: 3,
        semi_annually: 6,
        'semi-annually': 6,
        'semi annually': 6,
        semiannual: 6,
        annually: 12,
        annual: 12,
        yearly: 12,
    };

    if (frequency === 'at_maturity') {
        return formatCertificateHistoryDate(certificate.expiry_date);
    }

    const stepMonths = stepMonthsMap[frequency];
    if (!stepMonths) return '—';

    let baseline = issue;
    if (items && items.length) {
        const latest = items
            .map((x) => x.posting_date)
            .filter(Boolean)
            .sort()
            .slice(-1)[0];
        if (latest) {
            const latestDt = new Date(`${latest}T00:00:00`);
            if (!Number.isNaN(latestDt.getTime())) {
                baseline = latestDt;
            }
        }
    }

    const nextPosting = addMonthsKeepDay(baseline, stepMonths);
    return formatCertificateHistoryDateFromDate(nextPosting);
}