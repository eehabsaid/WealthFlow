'use strict';

function toggleTheme() {
    const html = document.documentElement;
    const isLight = html.getAttribute('data-theme') === 'light';
    const next    = isLight ? 'dark' : 'light';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    _updateThemeBtn(next);
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: next } }));
}

function _updateThemeBtn(theme) {
    const btn = document.getElementById('themeToggleBtn');
    if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
}

function applyStoredTheme() {
    const stored = localStorage.getItem('theme') || 'dark';
    if (stored === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    _updateThemeBtn(stored);
}

