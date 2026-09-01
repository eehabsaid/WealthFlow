"use strict";

async function exportExpenses() {
  const year = document.getElementById("fYear")?.value || "";
  const month = document.getElementById("fMonth")?.value || "";
  let url = "/api/expenses/?";
  if (year) url += `year=${year}&`;
  if (month) url += `month=${month}&`;
  const res = await fetch(url);
  const data = await res.json();

  const isAr = window.currentLang === "ar";
  const headers = [
    typeof t === "function" ? t("date") : "Date",
    typeof t === "function" ? t("category") : "Category",
    typeof t === "function" ? t("subcategory") : "Subcategory",
    typeof t === "function" ? t("description") : "Description",
    typeof t === "function" ? t("method") : "Method",
    typeof t === "function" ? t("amount") : "Amount",
    typeof t === "function" ? t("notes") : "Notes",
  ];

  const rows = [headers];
  (data.entries || []).forEach((e) => {
    let catName = e.category_name || "";
    let subcatName = e.subcategory_name || "";
    let payMethod = e.payment_method || "";

    if (typeof t === "function") {
      catName = t(catName, catName);
      subcatName = t(subcatName, subcatName);
      payMethod = t(payMethod, payMethod);
    }

    rows.push([
      formatDate(e.date),
      catName,
      subcatName,
      e.description || "",
      payMethod,
      e.amount,
      e.notes || "",
    ]);
  });

  const csv = rows
    .map((r) => r.map((v) => `"${String(v || "").replace(/"/g, '""')}"`).join(","))
    .join("\r\n");

  // Prepend UTF-8 BOM (\ufeff) so MS Excel opens Arabic characters natively in UTF-8
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `expenses_${year || "all"}_${month || "all"}.csv`;
  a.click();
  showToast(
    typeof t === "function" ? t("csv_exported", "CSV exported ✓") : "CSV exported ✓",
    "success"
  );
}

/* ╔══════════════════════════════════════════════════════════╗
   ║  CATEGORIES MANAGEMENT PAGE                              ║
   ╚══════════════════════════════════════════════════════════╝ */
