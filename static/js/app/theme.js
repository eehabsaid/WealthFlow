'use strict';

function toggleTheme() {
    const html = document.documentElement;
    const isLight = html.getAttribute('data-theme') === 'light';
    const next    = isLight ? 'dark' : 'light';
    if (next === 'light') {
        html.setAttribute('data-theme', 'light');
        html.setAttribute('data-bs-theme', 'light');
        if (document.body) {
            document.body.setAttribute('data-theme', 'light');
            document.body.setAttribute('data-bs-theme', 'light');
        }
    } else {
        html.setAttribute('data-theme', 'dark');
        html.setAttribute('data-bs-theme', 'dark');
        if (document.body) {
            document.body.setAttribute('data-theme', 'dark');
            document.body.setAttribute('data-bs-theme', 'dark');
        }
    }
    localStorage.setItem('theme', next);
    _updateThemeBtn(next);
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: next } }));
}

function _updateThemeBtn(theme) {
    const btns = document.querySelectorAll('#themeToggleBtn, #theme-toggle');
    btns.forEach(btn => {
        btn.textContent = theme === 'light' ? '☀️' : '🌙';
    });
}

function applyStoredTheme() {
    const stored = localStorage.getItem('theme') || 'dark';
    if (stored === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        document.documentElement.setAttribute('data-bs-theme', 'light');
        if (document.body) {
            document.body.setAttribute('data-theme', 'light');
            document.body.setAttribute('data-bs-theme', 'light');
        }
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        if (document.body) {
            document.body.setAttribute('data-theme', 'dark');
            document.body.setAttribute('data-bs-theme', 'dark');
        }
    }
    _updateThemeBtn(stored);
}

document.addEventListener('DOMContentLoaded', applyStoredTheme);
