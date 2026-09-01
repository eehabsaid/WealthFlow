"use strict";

async function saveExpense(expId) {
  const paymentMethod = document.getElementById("eMethod").value;
  const bankId = parseInt(document.getElementById("eBank")?.value) || null;
  if (isExpenseBankRequired(paymentMethod) && !bankId) {
    showToast(
      t("bank_account_required", "Bank account is required for Bank/Card payments"),
      "error"
    );
    return;
  }

  const body = {
    date: document.getElementById("eDate").value,
    amount: parseFloat(document.getElementById("eAmount").value) || 0,
    category_id: parseInt(document.getElementById("eCat").value) || null,
    subcategory_id: parseInt(document.getElementById("eSubcat").value) || null,
    description: document.getElementById("eDesc").value.trim(),
    payment_method: paymentMethod,
    bank_id: bankId,
    currency_id: parseInt(document.getElementById("eCurrency").value) || null,
    notes: document.getElementById("eNotes").value.trim(),
  };
  const url = expId ? `/api/expenses/${expId}/` : "/api/expenses/";
  const method = expId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Expense saved ✓", "success");
    renderExpenses();
    refreshFinancialViewsAfterExpenseChange();
  } else {
    let errorMsg = t("error_saving_expense", "Error saving expense");
    try {
      const payload = await res.json();
      if (payload?.error_key) {
        errorMsg = t(payload.error_key, payload.error || errorMsg);
      } else if (payload?.error) {
        errorMsg = payload.error;
      }
    } catch (_) {
      // keep fallback message
    }
    showToast(errorMsg, "error");
  }
}

async function deleteExpense(id) {
  if (!confirm("Delete this expense?")) return;
  const res = await fetch(`/api/expenses/${id}/`, { method: "DELETE" });
  if (!res.ok) {
    let errorMsg = t("error_deleting_expense", "Error deleting expense");
    try {
      const payload = await res.json();
      if (payload?.error_key) {
        errorMsg = t(payload.error_key, payload.error || errorMsg);
      } else if (payload?.error) {
        errorMsg = payload.error;
      }
    } catch (_) {
      // keep fallback message
    }
    showToast(errorMsg, "error");
    return;
  }
  showToast("Deleted");
  renderExpenses();
  refreshFinancialViewsAfterExpenseChange();
}

/* ── Export CSV ─────────────────────────────────────────────── */

async function saveCategory(catId) {
  const body = {
    name: document.getElementById("catName").value.trim(),
    icon: document.getElementById("catIcon").value.trim() || "💰",
    color_hex: document.getElementById("catColor").value,
  };
  if (!body.name) {
    showToast("Name required", "error");
    return;
  }
  const url = catId ? `/api/expense-categories/${catId}/` : "/api/expense-categories/";
  const method = catId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Category saved ✓", "success");
    renderExpenseCategories();
  } else showToast("Error", "error");
}

async function patchCategoryColor(id, hex) {
  await fetch(`/api/expense-categories/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ color_hex: hex }),
  });
}

async function deleteCategory(id) {
  if (!confirm("Delete this category and all its subcategories?")) return;
  await fetch(`/api/expense-categories/${id}/`, { method: "DELETE" });
  showToast("Deleted");
  renderExpenseCategories();
}

async function saveSubcategory(subId) {
  const name = document.getElementById(`sub_${subId}`)?.value.trim();
  if (!name) return;
  await fetch(`/api/expense-subcategories/${subId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  showToast(t("saved", "Saved ✓"), "success");
}

async function deleteSubcategory(subId, catId) {
  if (!confirm(t("confirm_delete_subcategory", "Delete this subcategory?"))) return;
  await fetch(`/api/expense-subcategories/${subId}/`, { method: "DELETE" });
  showToast(t("deleted", "Deleted"), "success");
  showSubcategoryModal(catId);
}
