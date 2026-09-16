"use strict";
// Year pill rendering and year switching for the employment/salary table.
// Part of the salary module (split from the former monolithic index.js,
// 200-line rule). Do not edit directly.

function renderYearPills(years, activeYear, companyId) {
  const container = document.getElementById("yearPills");
  if (!container) return;
  container.innerHTML = years
    .map(
      (y) => `
        <button class="year-pill ${y === activeYear ? "active" : ""}"
            onclick="switchYear(${y}, ${companyId})">${y}</button>`
    )
    .join("");
}

async function switchYear(year, companyId) {
  document
    .querySelectorAll(".year-pill")
    .forEach((p) => p.classList.toggle("active", parseInt(p.textContent) === year));
  const res = await fetch(`/api/salary/?company=${companyId}`);
  const data = await res.json();
  renderSalaryTable(data.entries, year, companyId);
}
