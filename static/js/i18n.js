// i18n.js — Language engine (translation loading, applying, t() helper)

'use strict';

// ── Module state ──────────────────────────────────────────────────────────
let _t    = {};
let _lang = localStorage.getItem('lang') || 'en';

// ════════════════════════════════════════════════════════════════════════════
// LANGUAGE LOADING
// ════════════════════════════════════════════════════════════════════════════

async function loadLanguage(code) {
    try {
        // Added cache buster to force the browser to download the newly injected translations
        const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
        if (!res.ok) throw new Error('Not found');

        _t    = await res.json();
        _lang = code;
        localStorage.setItem('lang', code);

        // RTL detection — normalise to string before comparing
        const rtlVal = String(_t.__rtl || '').toLowerCase();
        const isRTL  = rtlVal === 'true' || rtlVal === '1';
        document.documentElement.setAttribute('dir', isRTL ? 'rtl' : 'ltr');
        document.documentElement.lang = code;

        applyTranslations();

        // Persist active language to server
        await fetch('/api/settings/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ key: 'active_language', value: code }),
        });

        // Re-render active route so runtime-computed labels update immediately.
        if (window.__wfRouterReady && typeof window.route === 'function') {
            window.route();
        }

        document.dispatchEvent(new CustomEvent('languageChanged', { detail: { code } }));

    } catch (e) {
        console.warn('Language load failed:', e);
    }
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// APPLY TRANSLATIONS
// ════════════════════════════════════════════════════════════════════════════

function applyTranslations() {
    if (!_t) return;
    const lang = document.documentElement.lang || 'en';

    const formatTemplateValue = (name, value) => {
        const num = Number(value);
        if (!Number.isFinite(num)) return String(value ?? '');
        if (/(days|count|month|year|week)/i.test(name)) return fmtInt(num);
        if (/(ratio|trend|signal|gap|coverage|pct)/i.test(name)) return fmt(num);
        return fmtpresent(num);
    };

    const parseI18nParams = (raw) => {
        if (!raw) return {};
        const candidates = [raw];
        try {
            const decoded = decodeURIComponent(raw);
            if (decoded !== raw) candidates.push(decoded);
        } catch (_) {
            // Keep raw as the only candidate.
        }

        for (const candidate of candidates) {
            try {
                const parsed = JSON.parse(candidate);
                if (parsed && typeof parsed === 'object') return parsed;
            } catch (_) {
                // Try next candidate.
            }
        }
        return {};
    };

    const applyTemplateParams = (text, params) => {
        let out = String(text ?? '');
        Object.entries(params || {}).forEach(([name, value]) => {
            const replacement = formatTemplateValue(name, value);
            out = out.split(`{${name}}`).join(replacement);
        });
        return out;
    };

    // 1. Static text — [data-i18n]
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');

        // Ignore missing or empty translations
        if (!_t[key]) return;

        // Do not overwrite with empty values
        if (_t[key].trim() === "") return;

        el.textContent = _t[key];
    });

    // 2. Dynamic keys with template placeholders — [data-i18n-key]
    document.querySelectorAll('[data-i18n-key]').forEach(el => {
        const key = el.getAttribute('data-i18n-key');
        if (!key || !_t[key]) return;

        let text = _t[key];

        const templateParams = {
            ...parseI18nParams(el.getAttribute('data-i18n-params')),
        };

        const goldAmt  = el.getAttribute('data-gold-amount');
        const cashAmt  = el.getAttribute('data-cash-amount');
        const certAmt  = el.getAttribute('data-certificate-amount');
        const daysLeft = el.getAttribute('data-days-left');

        if (goldAmt  !== null) templateParams.gold_amount = goldAmt;
        if (cashAmt  !== null) templateParams.cash_amount = cashAmt;
        if (certAmt  !== null) templateParams.certificate_amount = certAmt;
        if (daysLeft !== null) templateParams.days_left = daysLeft;

        text = applyTemplateParams(text, templateParams);

        el.textContent = text;
    });

    // 2.5 Dynamic keys with template placeholders (HTML allowed) — [data-i18n-html-key]
    document.querySelectorAll('[data-i18n-html-key]').forEach(el => {
        const key = el.getAttribute('data-i18n-html-key');
        if (!key || !_t[key]) return;

        let text = _t[key];
        const templateParams = {
            ...parseI18nParams(el.getAttribute('data-i18n-params')),
        };

        text = applyTemplateParams(text, templateParams);
        el.innerHTML = text;
    });

    // 3. Prefix-based keys — [data-i18n-prefix] + [data-i18n-value]
    document.querySelectorAll('[data-i18n-prefix]').forEach(el => {
        const prefix = el.getAttribute('data-i18n-prefix');
        const raw    = el.getAttribute('data-i18n-value');
        if (!raw) { el.textContent = '—'; return; }
        const combined = `${prefix}${raw}`;
        el.textContent = _t[combined]
            || raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    });

    // 4. Attribute translators — placeholder and title
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (_t[key]) el.setAttribute('placeholder', _t[key]);
    });

    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (_t[key]) el.setAttribute('title', _t[key]);
    });

    // 5. Date formatting — .local-date-field[data-expiry]
    document.querySelectorAll('.local-date-field').forEach(td => {
        const raw = td.getAttribute('data-expiry');
        if (!raw) return;
        const d = new Date(raw);
        td.textContent = [
            d.toLocaleDateString(lang, { day:   '2-digit' }),
            d.toLocaleDateString(lang, { month: 'short'   }),
            d.toLocaleDateString(lang, { year:  'numeric' }),
        ].join('-');
    });

    // 6. Number formatter classes
    document.querySelectorAll('.num-fmt').forEach(el => {
        const v = el.getAttribute('data-value');
        if (v !== null) el.innerText = fmt(v);
    });
    document.querySelectorAll('.num-fmtpresent').forEach(el => {
        const v = el.getAttribute('data-value');
        if (v !== null) el.innerText = fmtpresent(v);
    });
    document.querySelectorAll('.num-fmtint').forEach(el => {
        const v = el.getAttribute('data-value');
        if (v !== null) el.innerText = fmtInt(v); 
    });
    document.querySelectorAll('.num-fmtRate').forEach(el => {
        const v = el.getAttribute('data-value');
        if (v !== null) el.innerText = fmtRate(v); 
    });

    // Auto-apply collapsible behaviour to any new tables rendered since last call
    if (typeof initCollapsibleTables === 'function') initCollapsibleTables();
}

// ════════════════════════════════════════════════════════════════════════════
// TRANSLATION HELPER — t(key, fallback)
// ════════════════════════════════════════════════════════════════════════════

function t(key, fallback) {
    if (typeof _t === 'undefined' || !_t) return fallback ?? key;

    const lang = localStorage.getItem('lang') || 'en';

    // Nested: _t[lang][key]
    if (_t[lang]?.[key]) return _t[lang][key];

    // Flat: _t[key]
    if (_t[key]) return _t[key];

    return fallback !== undefined ? fallback : key;
}

// ════════════════════════════════════════════════════════════════════════════
// CURRENT LANGUAGE ACCESSOR
// ════════════════════════════════════════════════════════════════════════════

function currentLang() {
    return _lang;
}