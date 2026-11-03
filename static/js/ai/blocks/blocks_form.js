"use strict";

/**
 * AI Workspace — editable expense card. The user can change every value before pressing Confirm.
 * The lists (categories + their subcategories, currencies, banks) are read live from the same endpoints the Expenses screen uses,
 * so whatever is changed in Expense Categories / Subcategories shows here. Nothing is hardcoded except the payment methods the app already defines.
 * Depends on: ai_core.js, blocks_core.js (calls it)
 */

const AIBlockForm = (() => {
  const lists = { categories: [], currencies: [], banks: [] };
  let loaded = false;
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  const T = (k, d) => _aiT(k, d);
  const INPUTS = { amount: "number", date: "date", description: "text", notes: "text" };

  async function load() {
    try {
      const [c, cur, b] = await Promise.all(
        ["/api/expense-categories/", "/api/currencies/", "/api/banks/"].map((u) =>
          fetch(u).then((r) => r.json())
        )
      );
      lists.categories = c.categories || [];
      lists.currencies = cur.currencies || [];
      lists.banks = (b.banks || []).filter((x) => x.is_active !== false);
    } catch (e) {
      return;
    }
    if (!loaded) {
      loaded = true;
      window.AIBlocks?.repaintPending();
    }
  }

  function select(field, value, names, attrs = "") {
    const all = value && !names.includes(value) ? [value, ...names] : names;
    const opts = ["", ...all].map(
      (n) => `<option value="${esc(n)}"${n === value ? " selected" : ""}>${esc(n || "—")}</option>`
    );
    return `<select class="form-select form-select-sm" data-ai-field="${field}" ${attrs}>${opts.join("")}</select>`;
  }

  function subNames(catName) {
    return ((lists.categories.find((c) => c.name === catName) || {}).subcategories || []).map(
      (s) => s.name
    );
  }

  function control(card, key, value) {
    if (INPUTS[key]) {
      const step = key === "amount" ? ' step="0.01" min="0"' : "";
      return `<input class="form-control form-control-sm" type="${INPUTS[key]}"${step} data-ai-field="${key}" value="${esc(value)}">`;
    }
    if (key === "category")
      return select(
        key,
        value,
        lists.categories.map((c) => c.name),
        'onchange="AIBlockForm.catChanged(this)"'
      );
    if (key === "subcategory") return select(key, value, subNames(card.category));
    if (key === "currency")
      return select(
        key,
        value,
        lists.currencies.map((c) => c.code)
      );
    if (key === "bank")
      return select(
        key,
        value,
        lists.banks.map((b) => b.name)
      );
    if (key === "payment_method")
      return select(
        key,
        value,
        (typeof PAYMENT_METHODS !== "undefined" ? PAYMENT_METHODS : []).map((m) => m.value)
      );
    return `<input class="form-control form-control-sm" data-ai-field="${esc(key)}" value="${esc(value)}">`;
  }

  /** The table rows of a pending, editable card. */
  function rows(p) {
    const now = {};
    (p.rows || []).forEach((r) => (now[r.label] = "after" in r ? r.after : r.value));
    return (p.rows || [])
      .map((r) => {
        const before = "after" in r ? `<s>${esc(r.before)}</s> → ` : "";
        return `<tr><th>${esc(T(r.label, r.label))}</th><td>${before}${control(now, r.label, now[r.label] ?? "")}</td></tr>`;
      })
      .join("");
  }

  function catChanged(sel) {
    const sub = sel.closest(".ai-act-card")?.querySelector('[data-ai-field="subcategory"]');
    if (sub) sub.outerHTML = select("subcategory", "", subNames(sel.value));
  }

  function collect(card) {
    const edits = {};
    card
      ?.querySelectorAll("[data-ai-field]")
      .forEach((el) => (edits[el.dataset.aiField] = el.value));
    return edits;
  }

  function showError(card, text) {
    let box = card?.querySelector(".ai-act-error");
    if (!box && card) {
      box = document.createElement("div");
      box.className = "ai-act-error small text-danger mt-1";
      card.querySelector(".ai-act-foot")?.before(box);
    }
    if (box) box.textContent = text;
  }

  load();
  return { rows, catChanged, collect, showError, refresh: load };
})();

window.AIBlockForm = AIBlockForm;
