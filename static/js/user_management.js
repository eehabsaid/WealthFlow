let currentPage = 1;
let pageSize = 25;
let currentQuery = "";

async function loadUsers(q = "", page = 1, size = 25) {
  currentQuery = q;
  currentPage = page;
  pageSize = size;
  const url = `/api/users/?q=${encodeURIComponent(q)}&page=${page}&page_size=${size}`;
  const res = await fetch(url);
  if (!res.ok) {
    console.error("Failed to load users");
    return;
  }
  const data = await res.json();
  const tbody = document.querySelector("#users-table tbody");
  tbody.innerHTML = "";
  data.users.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
            <td>${u.username}</td>
            <td>${u.email}</td>
            <td>${u.is_active ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>'}</td>
            <td>${u.is_staff ? '<span class="badge bg-info">Staff</span>' : ""}</td>
            <td>
                <button class="btn btn-sm btn-${u.is_active ? "warning" : "success"} btn-toggle-active" data-id="${u.id}">${u.is_active ? "Deactivate" : "Activate"}</button>
                <button class="btn btn-sm btn-danger btn-delete" data-id="${u.id}">Delete</button>
                <button class="btn btn-sm btn-outline-primary btn-perms" data-id="${u.id}">Permissions</button>
            </td>
        `;
    tbody.appendChild(tr);
  });
  // pagination info
  const info = document.getElementById("pagination-info");
  if (info) {
    info.textContent = `Showing ${data.users.length} of ${data.total || data.users.length} users — Page ${data.page} / ${data.num_pages || 1}`;
  }
  const cur = document.getElementById("current-page");
  if (cur) cur.textContent = String(data.page || 1);
  attachHandlers();
}

function attachHandlers() {
  document.querySelectorAll(".btn-toggle-active").forEach((b) => {
    b.onclick = async () => {
      const id = b.dataset.id;
      const isActivate = b.textContent.trim() === "Activate";
      const resp = await fetch("/api/users/" + id + "/", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: isActivate }),
      });
      if (resp.ok) loadUsers(currentQuery, currentPage, pageSize);
    };
  });
  document.querySelectorAll(".btn-delete").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("Delete user?")) return;
      const id = b.dataset.id;
      const resp = await fetch("/api/users/" + id + "/", { method: "DELETE" });
      if (resp.ok) loadUsers(currentQuery, currentPage, pageSize);
    };
  });
  document.querySelectorAll(".btn-perms").forEach((b) => {
    b.onclick = async () => {
      const id = b.dataset.id;
      await openPermissionsModal(id);
    };
  });
}

let currentPermUserId = null;
const permModal = new bootstrap.Modal(
  document.getElementById("permissionsModal"),
);

async function openPermissionsModal(userId) {
  currentPermUserId = userId;
  // load available pages
  const pagesRes = await fetch("/api/users/permissions/pages/");
  const pagesData = pagesRes.ok
    ? await pagesRes.json()
    : { available_pages: [] };
  const select = document.getElementById("perm-select");
  select.innerHTML = "";
  pagesData.available_pages.forEach(([key, label]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = label;
    select.appendChild(opt);
  });
  // load user perms
  await refreshPermList();
  permModal.show();
}

async function refreshPermList() {
  const list = document.getElementById("perm-list");
  list.innerHTML = "";
  const res = await fetch("/api/users/" + currentPermUserId + "/permissions/");
  if (!res.ok) return;
  const data = await res.json();
  data.permissions.forEach((p) => {
    const div = document.createElement("div");
    div.className = "d-flex align-items-center justify-content-between mb-1";
    div.innerHTML = `<div>${p.page}</div><div><button data-id="${p.id}" class="btn btn-sm btn-danger btn-del-perm">Remove</button></div>`;
    list.appendChild(div);
  });
  document.querySelectorAll(".btn-del-perm").forEach(
    (b) =>
      (b.onclick = async () => {
        const id = b.dataset.id;
        const r = await fetch("/api/users/permissions/" + id + "/", {
          method: "DELETE",
        });
        if (r.ok) refreshPermList();
      }),
  );
}

document.getElementById("perm-add").onclick = async () => {
  const select = document.getElementById("perm-select");
  const page = select.value;
  if (!page) return;
  const res = await fetch("/api/users/" + currentPermUserId + "/permissions/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page }),
  });
  if (res.ok) refreshPermList();
};

// search
const searchInput = document.getElementById("search");
let searchTimeout = null;
if (searchInput) {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(
      () => loadUsers(searchInput.value.trim(), 1, pageSize),
      300,
    );
  });
}

// page size selector
const pageSizeEl = document.getElementById("page-size");
if (pageSizeEl) {
  pageSizeEl.value = String(pageSize);
  pageSizeEl.addEventListener("change", () => {
    const s = parseInt(pageSizeEl.value) || 25;
    loadUsers(currentQuery, 1, s);
  });
}

// prev/next
const prevBtn = document.getElementById("prev-page");
const nextBtn = document.getElementById("next-page");
if (prevBtn)
  prevBtn.onclick = () => {
    if (currentPage > 1) loadUsers(currentQuery, currentPage - 1, pageSize);
  };
if (nextBtn)
  nextBtn.onclick = () => {
    loadUsers(currentQuery, currentPage + 1, pageSize);
  };

// initial load
loadUsers("", 1, pageSize);
