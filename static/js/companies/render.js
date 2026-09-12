// companies.js — All Companies management page (render)

"use strict";

async function renderAllCompanies() {
  const mc = document.getElementById("main-content");
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const res = await fetch("/api/companies/");
  const data = await res.json();
  const companies = data.companies || [];

  const emptyMessage = `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-secondary)" data-i18n="no_data">No companies found</td></tr>`;

  const rows = companies
    .map(
      (c) => `
            <tr>
                <td>
                    <span class="nav-dot" style="background:${c.color_hex};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px"></span>
                    <strong>${c.name}</strong>
                    ${c.display_name && c.display_name !== c.name ? `<br><small style="color:var(--text-secondary)">${c.display_name}</small>` : ""}
                </td>
                <td>${c.group_name || "-"}</td>
                <td><span class="badge" style="background:${c.color_hex}22;color:${c.color_hex};border:1px solid ${c.color_hex}">${c.color_hex}</span></td>
                <td>${c.is_active ? `<span class="badge bg-success" data-i18n="is_active">Active</span>` : `<span class="badge bg-secondary" data-i18n="inactive">Inactive</span>`}</td>
                <td style="text-align:center">
                    <button class="btn-icon" onclick="showCompanyModal(${c.id})" title="${t("btn_edit", "Edit")}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon" onclick="deleteCompany(${c.id})" title="${t("btn_delete", "Delete")}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>`
    )
    .join("");

  mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_all_companies">All Companies</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="company">Company</th>
                            <th data-i18n="group">Group</th>
                            <th data-i18n="color">Color</th>
                            <th data-i18n="status">Status</th>
                            <th style="text-align:center;width:80px" data-i18n="actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>${rows || emptyMessage}</tbody>
                </table>
            </div>
        </div>`;
  applyTranslations();
}

