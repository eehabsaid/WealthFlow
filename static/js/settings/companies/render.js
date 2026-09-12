"use strict";
// Company configuration settings — render
// This file is part of the settings module. Do not edit directly.

async function renderCompanySettings() {
  const res = await fetch("/api/companies/");
  const { companies = [] } = await res.json();

  const rows = companies
    .map(
      (c) => `
        <tr>
            <td>
                <span style="background:${c.color_hex};width:12px;height:12px;border-radius:3px;
                             display:inline-block;margin-right:8px"></span>${c.name}
            </td>
            <td>${c.display_name}</td>
            <td><span class="group-badge">${c.group_name || "—"}</span></td>
            <td>
                <input type="color" value="${c.color_hex}"
                    onchange="updateCompanyColor(${c.id}, this.value)"
                    style="background:none;border:none;width:32px;height:32px;cursor:pointer">
            </td>
            <td>${c.order}</td>
            <td>
                <span style="color:${c.is_active ? "var(--accent-green)" : "var(--accent-red)"}"
                    data-i18n="${c.is_active ? "active" : "inactive"}">
                </span>
            </td>
            <td>
                <button class="btn-icon" onclick="showCompanyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCompany(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  const contentEl = document.getElementById("settingsContent");
  if (!contentEl) return;
  contentEl.innerHTML = `
        <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:14px">
            
            <button class="btn-primary-custom" onclick="showCompanyModal(null)" data-i18n="btn_add">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="company_name">Name</th>
                    <th data-i18n="company_display_name">Display Name</th>
                    <th data-i18n="group_name">Group</th>
                    <th data-i18n="color">Color</th>
                    <th data-i18n="order">Order</th>
                    <th data-i18n="active">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
  applyTranslations();
}

