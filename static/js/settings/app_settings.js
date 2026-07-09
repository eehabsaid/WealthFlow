"use strict";
// General app settings helper
// This file is part of the settings module. Do not edit directly.

function saveAppSetting(key, value) {
    fetch('/api/settings/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ key, value }),
    }).then(() => showToast(t('settings_saved', 'Settings saved ✓')));
}

