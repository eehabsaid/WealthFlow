"use strict";

function doLogout() {
  // Use GET redirect to the Django logout view (no CSRF token needed)
  window.location.href = "/accounts/logout/";
}

function showProfileModal() {
  const u = window._currentUser || {};
  const name = u.display_name || u.full_name || u.username || "";
  const birthday = u.birthday || "";
  const initials = name ? name.charAt(0).toUpperCase() : "?";
  const avatar = u.avatar_url
    ? `<img src="${u.avatar_url}" id="avatarPreview"
               style="width:90px;height:90px;border-radius:50%;object-fit:cover;
                      border:3px solid var(--border-color)">`
    : `<div id="avatarPreview"
               style="width:90px;height:90px;border-radius:50%;
                      background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                      display:inline-flex;align-items:center;justify-content:center;
                      font-size:36px;font-weight:700;color:#fff;
                      border:3px solid var(--border-color)">
               ${initials}
           </div>`;

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title">
                <i class="bi bi-person-circle" style="color:var(--accent-primary);margin-right:8px"></i>
                ${t("profile_modal_title", "My Profile")}
            </h5>
            <button type="button" class="btn-close btn-close-white"
                    data-bs-dismiss="modal" onclick="closeModal()"></button>
        </div>
        <div class="modal-body">
            <div style="text-align:center;margin-bottom:22px">
                <div style="position:relative;display:inline-block">
                    ${avatar}
                    <label for="avatarInput"
                           style="position:absolute;bottom:2px;right:2px;
                                  background:var(--accent-primary);color:#fff;
                                  width:28px;height:28px;border-radius:50%;
                                  display:flex;align-items:center;justify-content:center;
                                  cursor:pointer;font-size:13px;border:2px solid var(--bg-secondary)"
                           title="${t("profile_upload_photo", "Upload photo")}">
                        <i class="bi bi-camera"></i>
                    </label>
                    <input type="file" id="avatarInput" accept="image/*" style="display:none"
                           onchange="window.previewAndUploadAvatar(this)">
                </div>
                <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">
                    ${t("profile_click_camera_hint", "Click the camera icon to change your photo")}
                </div>
            </div>
            <div class="row g-3">
                <div class="col-12">
                    <label class="form-label">${t("profile_full_name", "Full Name")}</label>
                    <input type="text" class="form-control" id="profileFullName"
                           value="${name}" placeholder="${t("profile_full_name_placeholder", "e.g. Ehab Mohamed")}">
                </div>
                <div class="col-12">
                    <label class="form-label">${t("profile_username", "Username")}</label>
                    <input type="text" class="form-control"
                           value="${u.username || ""}" disabled style="opacity:.6">
                </div>
                <div class="col-12">
                    <label class="form-label">${t("profile_email", "Email")}</label>
                    <input type="text" class="form-control"
                           value="${u.email || ""}" disabled style="opacity:.6">
                </div>
                <div class="col-12">
                    <label class="form-label">${t("profile_birthday_optional", "Birthday (Optional)")}</label>
                    <input type="date" class="form-control" id="profileBirthday"
                           value="${birthday}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal"
                    onclick="closeModal()">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="window.saveProfile()">
                <i class="bi bi-floppy"></i> ${t("btn_save", "Save")}
            </button>
        </div>`);
}

async function previewAndUploadAvatar(input) {
  const file = input.files[0];
  if (!file) return;

  // Preview immediately
  const reader = new FileReader();
  reader.onload = (e) => {
    const prev = document.getElementById("avatarPreview");
    if (prev)
      prev.outerHTML = `<img id="avatarPreview" src="${e.target.result}"
            style="width:90px;height:90px;border-radius:50%;object-fit:cover;
                   border:3px solid var(--border-color)">`;
  };
  reader.readAsDataURL(file);

  // Upload
  const fd = new FormData();
  fd.append("avatar", file);
  try {
    const res = await fetch("/api/auth/profile/avatar/", { method: "POST", body: fd });
    const data = await res.json();
    if (res.ok) {
      if (window._currentUser) window._currentUser.avatar_url = data.avatar_url;
      showToast("Photo updated ✓");
      renderSidebar();
    } else {
      showToast("Upload failed: " + (data.error || ""), "error");
    }
  } catch (e) {
    showToast("Upload error: " + e.message, "error");
  }
}

async function saveProfile() {
  const fullName = document.getElementById("profileFullName")?.value.trim() || "";
  const birthday = document.getElementById("profileBirthday")?.value || "";
  try {
    const res = await fetch("/api/auth/profile/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, birthday }),
    });
    const data = await res.json();
    if (res.ok) {
      if (window._currentUser) {
        window._currentUser.full_name = data.profile.full_name;
        window._currentUser.display_name = data.profile.display_name;
        window._currentUser.birthday = data.profile.birthday || "";
      }
      closeModal();
      showToast("Profile saved ✓");
      renderSidebar();
    } else {
      showToast("Error: " + (data.error || ""), "error");
    }
  } catch (e) {
    showToast("Error: " + e.message, "error");
  }
}

// ════════════════════════════════════════════════════════════════════════════
// MISC HELPERS
// ════════════════════════════════════════════════════════════════════════════
