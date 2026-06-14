// profile.js — User Profile, Preferences & Security (Features 6 & 7)

async function renderProfile() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const [profRes, prefRes, actRes] = await Promise.all([
        fetch('/api/profile/'),
        fetch('/api/user-preferences/'),
        fetch('/api/login-activity/'),
    ]);

    const profData = await profRes.json();
    const prefData = await prefRes.json();
    const actData  = await actRes.json();

    const profile  = profData.profile  || {};
    const user     = profData.user     || {};
    const prefs    = prefData.preferences || {};
    const acts     = actData.activities   || [];

    const actRows = acts.slice(0, 10).map(a => `
        <tr>
            <td style="white-space:nowrap;font-size:12px;color:var(--text-muted)">${a.timestamp}</td>
            <td><span style="color:${a.success ? 'var(--accent-green)' : 'var(--accent-danger)'};font-weight:700">${a.success ? '✓ Success' : '✗ Failed'}</span></td>
            <td style="font-size:12px;color:var(--text-muted)">${a.ip_address || '—'}</td>
            <td style="font-size:11px;color:var(--text-muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(a.user_agent)}">${esc(a.user_agent ? a.user_agent.substring(0,60)+'…' : '—')}</td>
        </tr>`).join('');

    const avatarSrc = profile.avatar_url
        ? `<img src="${profile.avatar_url}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid var(--accent-primary)">`
        : `<div style="width:80px;height:80px;border-radius:50%;background:var(--accent-primary);display:flex;align-items:center;justify-content:center;font-size:32px;color:#fff;font-weight:700">${(user.username||'?')[0].toUpperCase()}</div>`;

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_profile">👤 Profile & Preferences</div></div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">

            <!-- Profile card -->
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:24px">
                <div style="font-weight:700;color:var(--text-primary);margin-bottom:18px;font-size:15px" data-i18n="profile_info">Profile Information</div>
                <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
                    ${avatarSrc}
                    <div>
                        <div style="font-size:18px;font-weight:700;color:var(--text-primary)">${esc(profile.full_name || user.username)}</div>
                        <div style="color:var(--text-muted);font-size:13px">${esc(user.email || '')}</div>
                        <div style="color:var(--text-muted);font-size:12px;margin-top:2px">${user.is_staff ? '⚡ Admin' : '👤 User'}</div>
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:12px">
                    <div>
                        <label style="font-size:12px;color:var(--text-muted)" data-i18n="profile_full_name">Full Name</label>
                        <input id="profileFullName" class="form-control" value="${esc(profile.full_name || '')}" style="margin-top:4px">
                    </div>
                    <div>
                        <label style="font-size:12px;color:var(--text-muted)" data-i18n="profile_bio">Bio</label>
                        <textarea id="profileBio" class="form-control" rows="2" style="margin-top:4px">${esc(profile.bio || '')}</textarea>
                    </div>
                    <div>
                        <label style="font-size:12px;color:var(--text-muted)" data-i18n="profile_avatar">Profile Picture (base64 or URL)</label>
                        <input id="profileAvatarFile" type="file" accept="image/*" class="form-control" style="margin-top:4px" onchange="previewAvatar(this)">
                    </div>
                    <button class="btn-primary-custom" onclick="saveProfile()" data-i18n="save_profile">Save Profile</button>
                </div>
            </div>

            <!-- Preferences card -->
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:24px">
                <div style="font-weight:700;color:var(--text-primary);margin-bottom:18px;font-size:15px" data-i18n="profile_preferences">Preferences</div>
                <div style="display:flex;flex-direction:column;gap:14px">
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="prefCertExpiry" ${prefs.notify_cert_expiry ? 'checked' : ''}>
                        <span data-i18n="pref_notify_cert">Notify on certificate expiry</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="prefSalary" ${prefs.notify_salary ? 'checked' : ''}>
                        <span data-i18n="pref_notify_salary">Salary reminders</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="prefSystem" ${prefs.notify_system ? 'checked' : ''}>
                        <span data-i18n="pref_notify_system">System notifications</span>
                    </label>
                    <button class="btn-primary-custom" onclick="savePreferences()" style="margin-top:8px" data-i18n="save_preferences">Save Preferences</button>
                </div>

                <!-- Change Password -->
                <div style="margin-top:28px;padding-top:20px;border-top:1px solid var(--border-color)">
                    <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;font-size:15px" data-i18n="change_password">Change Password</div>
                    <div style="display:flex;flex-direction:column;gap:10px">
                        <input type="password" id="pwdCurrent" class="form-control" placeholder="${t('pwd_current','Current password')}">
                        <input type="password" id="pwdNew" class="form-control" placeholder="${t('pwd_new','New password')}">
                        <input type="password" id="pwdConfirm" class="form-control" placeholder="${t('pwd_confirm','Confirm new password')}">
                        <button class="btn-secondary-custom" onclick="changePassword()" data-i18n="change_password">Change Password</button>
                    </div>
                </div>
            </div>

        </div>

        <!-- Login Activity -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:24px;margin-top:20px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;font-size:15px" data-i18n="login_activity">Recent Login Activity</div>
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="audit_timestamp">Timestamp</th>
                    <th data-i18n="login_status">Status</th>
                    <th data-i18n="audit_ip">IP Address</th>
                    <th data-i18n="login_agent">Browser / Device</th>
                </tr></thead>
                <tbody>${actRows || `<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-muted)" data-i18n="no_records">No records</td></tr>`}</tbody>
            </table>
            </div>
        </div>`;

    applyTranslations();
}

function previewAvatar(input) {
    if (!input.files || !input.files[0]) return;
    const reader = new FileReader();
    reader.onload = e => {
        window._avatarB64 = e.target.result;
    };
    reader.readAsDataURL(input.files[0]);
}

async function saveProfile() {
    const body = {
        full_name: document.getElementById('profileFullName').value.trim(),
        bio:       document.getElementById('profileBio').value.trim(),
    };
    if (window._avatarB64) body.avatar_b64 = window._avatarB64;

    const res = await fetch('/api/profile/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (res.ok) {
        showToast(t('profile_saved', 'Profile saved ✓'));
        window._avatarB64 = null;
        renderProfile();
    } else {
        const d = await res.json();
        showToast(d.error || t('error_generic','Error saving profile'), 'error');
    }
}

async function savePreferences() {
    const body = {
        notify_cert_expiry: document.getElementById('prefCertExpiry').checked,
        notify_salary:      document.getElementById('prefSalary').checked,
        notify_system:      document.getElementById('prefSystem').checked,
    };
    const res = await fetch('/api/user-preferences/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (res.ok) {
        showToast(t('preferences_saved', 'Preferences saved ✓'));
    } else {
        showToast(t('error_generic','Error'), 'error');
    }
}

async function changePassword() {
    const body = {
        current_password:  document.getElementById('pwdCurrent').value,
        new_password:      document.getElementById('pwdNew').value,
        confirm_password:  document.getElementById('pwdConfirm').value,
    };
    if (!body.current_password || !body.new_password) {
        showToast(t('pwd_fill_all','Please fill all password fields'), 'error');
        return;
    }
    const res = await fetch('/api/change-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (res.ok) {
        showToast(t('pwd_changed', 'Password changed successfully ✓'));
        document.getElementById('pwdCurrent').value = '';
        document.getElementById('pwdNew').value     = '';
        document.getElementById('pwdConfirm').value = '';
    } else {
        showToast(data.error || t('error_generic','Error'), 'error');
    }
}

function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
