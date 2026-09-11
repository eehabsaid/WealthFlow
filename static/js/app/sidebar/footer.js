"use strict";
function _renderSidebarFooter(sidebar) {
  const u = window._currentUser || {};
  const uName = u.display_name || u.full_name || u.username || "Guest";
  const avatar = u.avatar_url
    ? `<img src="${u.avatar_url}"
               style="width:36px;height:36px;border-radius:50%;object-fit:cover;
                      border:2px solid var(--border-color);flex-shrink:0">`
    : `<div style="width:36px;height:36px;border-radius:50%;
                       background:linear-gradient(135deg,var(--accent-primary),#0f45c8);
                       display:flex;align-items:center;justify-content:center;
                       font-size:15px;font-weight:700;color:#fff;flex-shrink:0">
               ${uName.charAt(0).toUpperCase()}
           </div>`;

  const nav = sidebar.querySelector(".sidebar-nav");
  if (!nav) return;

  // Remove existing footer to prevent duplicates
  const old = nav.querySelector(".user-sidebar-footer");
  if (old) old.remove();

  const footer = document.createElement("div");
  footer.className = "user-sidebar-footer";
  footer.style.cssText =
    "border-top:1px solid var(--border-color);padding:10px 8px 8px;margin-top:auto";
  footer.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;
                    cursor:pointer;transition:background .15s"
             onclick="window.showProfileModal && window.showProfileModal()"
             onmouseenter="this.style.background='var(--bg-tertiary)'"
             onmouseleave="this.style.background='transparent'"
             title="${t("click_to_edit_profile", "Edit profile")}">
            ${avatar}
            <div style="overflow:hidden;flex:1;min-width:0" class="nav-text">
                <div style="font-size:13px;font-weight:600;color:var(--text-primary);
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    ${uName}
                </div>
                <div style="font-size:11px;color:var(--text-muted)">${u.email || ""}</div>
            </div>
            <i class="bi bi-pencil-square nav-text"
               style="color:var(--text-muted);font-size:13px;flex-shrink:0"></i>
        </div>
        <button onclick="window.doLogout && window.doLogout()"
                style="width:100%;display:flex;align-items:center;gap:9px;padding:8px 12px;
                       border:none;background:none;color:var(--accent-red,#ff4d6d);cursor:pointer;
                       border-radius:8px;font-size:13.5px;font-weight:600;
                       transition:background .15s;margin-top:2px"
                onmouseenter="this.style.background='rgba(255,77,109,0.1)'"
                onmouseleave="this.style.background='none'">
            <i class="bi bi-box-arrow-left" style="font-size:16px"></i>
            <span class="nav-text" data-i18n="nav_logout">Logout</span>
        </button>`;
  nav.appendChild(footer);
}

