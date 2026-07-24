'use strict';

(function () {
    const LANG_STORAGE_KEY = 'lang';
    const selector = () => document.getElementById('authLanguageSelect');

    function getCookie(name) {
        const cookieStr = document.cookie || '';
        const parts = cookieStr.split(';');
        for (let i = 0; i < parts.length; i += 1) {
            const part = parts[i].trim();
            if (part.startsWith(`${name}=`)) {
                return decodeURIComponent(part.substring(name.length + 1));
            }
        }
        return '';
    }

    function syncCsrfInputs() {
        const token = getCookie('csrftoken');
        if (!token) {
            return;
        }
        document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
            input.value = token;
        });
    }

    async function loadLanguage(code) {
        const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
        if (!res.ok) {
            return;
        }

        const translations = await res.json();
        localStorage.setItem(LANG_STORAGE_KEY, code);
        document.cookie = `wf_lang=${code}; path=/; max-age=31536000; samesite=lax`;
        document.documentElement.lang = code;
        let isRTL = false;
        try {
            const sRes = await fetch(`/api/settings/?v=${Date.now()}`);
            if (sRes.ok) {
                const sData = await sRes.json();
                const langs = JSON.parse(sData.settings?.available_languages || '[]');
                const found = langs.find((l) => l.code === code);
                if (found !== undefined && found.rtl !== undefined) {
                    isRTL = found.rtl === true || found.rtl === 'true' || found.rtl === 1;
                } else {
                    const rtlVal = String(translations.__rtl || '').toLowerCase();
                    isRTL = rtlVal === 'true' || rtlVal === '1';
                }
            } else {
                const rtlVal = String(translations.__rtl || '').toLowerCase();
                isRTL = rtlVal === 'true' || rtlVal === '1';
            }
        } catch (e) {
            const rtlVal = String(translations.__rtl || '').toLowerCase();
            isRTL = rtlVal === 'true' || rtlVal === '1';
        }
        document.documentElement.dir = isRTL ? 'rtl' : 'ltr';

        document.querySelectorAll('.lang-hidden-input').forEach((input) => {
            input.value = code;
        });

        document.querySelectorAll('[data-i18n]').forEach((el) => {
            const key = el.getAttribute('data-i18n');
            if (key && translations[key]) {
                el.textContent = translations[key];
            }
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (key && translations[key]) {
                el.setAttribute('placeholder', translations[key]);
            }
        });

        document.querySelectorAll('[data-i18n-title]').forEach((el) => {
            const key = el.getAttribute('data-i18n-title');
            if (key && translations[key]) {
                el.setAttribute('title', translations[key]);
            }
        });

        if (document.title && document.querySelector('title[data-i18n]')) {
            const key = document.querySelector('title[data-i18n]').getAttribute('data-i18n');
            if (key && translations[key]) {
                document.title = translations[key];
            }
        }

        const select = selector();
        if (select) {
            select.value = code;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const select = selector();
        const current = localStorage.getItem(LANG_STORAGE_KEY) || document.documentElement.lang || 'en';
        syncCsrfInputs();

        document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
            form.addEventListener('submit', () => {
                syncCsrfInputs();
            });
        });

        if (select) {
            select.value = current;
            select.addEventListener('change', (event) => {
                loadLanguage(event.target.value);
            });
        }
        loadLanguage(current);
    });
})();