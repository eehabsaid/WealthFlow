'use strict';

async function exportExpenses() {
  const year = document.getElementById("fYear")?.value || "";
  const month = document.getElementById("fMonth")?.value || "";
  let url = "/api/expenses/?";
  if (year) url += `year=${year}&`;
  if (month) url += `month=${month}&`;
  const res = await fetch(url);
  const data = await res.json();
  const rows = [
    [
      "Date",
      "Category",
      "Subcategory",
      "Description",
      "Method",
      "Amount",
      "Notes",
    ],
  ];
  (data.entries || []).forEach((e) => {
    rows.push([
      formatDate(e.date),
      e.category_name,
      e.subcategory_name,
      e.description,
      e.payment_method,
      e.amount,
      e.notes,
    ]);
  });
  const csv = rows
    .map((r) =>
      r.map((v) => `"${String(v || "").replace(/"/g, '""')}"`).join(","),
    )
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `expenses_${year}_${month}.csv`;
  a.click();
  showToast("CSV exported ✓", "success");
}

/* ╔══════════════════════════════════════════════════════════╗
   ║  CATEGORIES MANAGEMENT PAGE                              ║
   ╚══════════════════════════════════════════════════════════╝ */