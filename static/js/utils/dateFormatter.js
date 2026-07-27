/**
 * Centralized Date Formatter for WealthFlow (Frontend)
 * Formats user-visible dates into localized 'dd-mmm-yyyy' format using translation keys month_short_1..month_short_12.
 * Preserves time components if present and falls back gracefully to the input string if parsing fails.
 *
 * Examples:
 *   English: 27-Jul-2026 / 05-Jan-2026
 *   French:  27-juil.-2026 / 05-janv.-2026
 *   Arabic:  27-يوليو-2026 / 05-يناير-2026
 *   German:  27-Jul-2026 / 05-Jan-2026
 */
'use strict';

function formatDate(value, lang) {
    if (value === null || value === undefined) return '';
    const strVal = String(value).trim();
    if (!strVal) return '';
    if (strVal === '-') return '-';

    try {
        let dt = null;
        let timePart = '';

        if (value instanceof Date) {
            if (!isNaN(value.getTime())) {
                dt = value;
                const hrs = String(value.getHours()).padStart(2, '0');
                const mins = String(value.getMinutes()).padStart(2, '0');
                const secs = String(value.getSeconds()).padStart(2, '0');
                if (hrs !== '00' || mins !== '00' || secs !== '00') {
                    timePart = secs !== '00' ? ` ${hrs}:${mins}:${secs}` : ` ${hrs}:${mins}`;
                }
            }
        } else if (typeof value === 'string' || typeof value === 'number') {
            // Check ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS / YYYY-MM-DD HH:MM:SS
            const isoMatch = strVal.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}:\d{2}(?::\d{2})?))?/);
            if (isoMatch) {
                const y = parseInt(isoMatch[1], 10);
                const m = parseInt(isoMatch[2], 10) - 1;
                const d = parseInt(isoMatch[3], 10);
                dt = new Date(y, m, d);
                if (isoMatch[4]) {
                    timePart = ` ${isoMatch[4]}`;
                }
            } else {
                // Check DD-MM-YYYY or DD/MM/YYYY or DD-MM-YYYY HH:MM
                const dmyMatch = strVal.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?/);
                if (dmyMatch) {
                    const d = parseInt(dmyMatch[1], 10);
                    const m = parseInt(dmyMatch[2], 10) - 1;
                    const y = parseInt(dmyMatch[3], 10);
                    dt = new Date(y, m, d);
                    if (dmyMatch[4]) {
                        timePart = ` ${dmyMatch[4]}`;
                    }
                } else {
                    const parsed = new Date(strVal);
                    if (!isNaN(parsed.getTime())) {
                        dt = parsed;
                    }
                }
            }
        }

        if (dt && !isNaN(dt.getTime())) {
            const activeLang = lang || (typeof currentLang === 'function' ? currentLang() : (localStorage.getItem('lang') || 'en'));
            const dayStr = String(dt.getDate()).padStart(2, '0');
            const monthIndex = dt.getMonth() + 1;
            const monthKey = `month_short_${monthIndex}`;

            const monthName = (typeof t === 'function')
                ? t(monthKey, dt.toLocaleString('en-US', { month: 'short' }))
                : monthKey;

            const yearStr = String(dt.getFullYear());

            return `${dayStr}-${monthName}-${yearStr}${timePart}`;
        }
    } catch (e) {
        // Fallback safely to original string on any error
    }

    return strVal;
}

if (typeof window !== 'undefined') {
    window.formatDate = formatDate;
}
