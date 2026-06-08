// i18n.js — language engine
let _t = {};
let _lang = localStorage.getItem('lang') || 'en';

async function loadLanguage(code) {
    try {
        const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
        if (!res.ok) throw new Error('Not found');
        _t = await res.json();
        _lang = code;
        localStorage.setItem('lang', code);
        const isRTL = _t.__rtl === true;
        document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
        document.documentElement.lang = code;
        applyTranslations();
        await fetch('/api/settings/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key: 'active_language', value: code})
        });
    } catch(e) { console.warn('Language load failed:', e); }
}

function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const k = el.getAttribute('data-i18n');
        if (_t[k]) el.textContent = _t[k];
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const k = el.getAttribute('data-i18n-ph');
        if (_t[k]) el.placeholder = _t[k];
    });
}

function t(key, fallback) {
    return _t[key] || fallback || key;
}

function currentLang() { return _lang; }
