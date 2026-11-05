# Task 20261105-110049-inspect-how-wealthflow-handles
Goal: Inspect how WealthFlow handles expense categories and subcategories. Trace the relevant Django models, services, API endpoints, frontend JavaScript, and translation files. Explain how a new expense category is created and used. Identify any inconsistencies between backend and frontend. Do not modify anything. List the exact files involved and explain their responsibilities.
Status: ANSWERED

## Answer (no file changes were made)
Read-only investigation complete. WealthFlow expense categories/subcategories work as follows.

MODELS — core/models/expenses.py
- ExpenseCategory: owner FK (multi-tenant), name, icon, color_hex, order; unique_together [owner, name]; to_dict() exposes id/name/icon/color_hex/order.
- ExpenseSubcategory: category FK (CASCADE, related_name subcategories), name, order; unique_together [category, name]; to_dict() includes category id/name/icon/color. No owner FK — ownership inherited via parent category.
- Expense: category and subcategory are both nullable SET_NULL FKs (so deleting a category nulls expenses rather than cascading).

SERVICES — category/subcategory CRUD has NO service layer; it's written directly in the views (unlike Expense rows which go through ExpenseService). This is an architectural inconsistency: the skills say business logic belongs in a service, but category creation mutates models directly in views.

VIEWS — core/views/expense_category_views.py
- ExpenseCategoryListView GET (lists cats + nested subcategories), POST (creates category).
- ExpenseCategoryDetailView PUT/DELETE (delete cascades subcategories).
- ExpenseSubcategoryListView POST (create sub).
- ExpenseSubcategoryDetailView PUT/DELETE.
- All start with _api_auth_required; ownership via _owned_object_or_404 / _child_owned_object_or_404 (parent_field="category").

URLS — core/urls/financial_core_urls.py lines 48-54: api/expense-categories/, api/expense-categories/<pk>/, api/expense-subcategories/, api/expense-subcategories/<pk>/.

FRONTEND (vanilla JS, static/js/expenses/)
- categories.js: renderExpenseCategories() + showCategoryModal(); UI for add/edit/delete category, color picker.
- subcategories.js: showSubcategoryModal(), addSubcategory(), saveSubcategory(), deleteSubcategory(); manages subs inside a category modal.
- api.js: saveCategory(), patchCategoryColor(), deleteCategory(), saveSubcategory(), deleteSubcategory() — the fetch calls.
- categories.js/subcategories.js/api.js are the three files directly responsible.

HOW A NEW CATEGORY IS CREATED
1. User clicks "Add Category" → showCategoryModal(null) renders form (name/icon/color).
2. Save → saveCategory(null) in api.js POSTs {name, icon, color_hex} to /api/expense-categories/.
3. ExpenseCategoryListView.post creates the row (owner=request.user) and returns to_dict (201).
4. renderExpenseCategories() refreshes; subcategories added later via addSubcategory() → POST /api/expense-subcategories/ with {category_id, name}.

INCONSISTENCIES FOUND (backend vs frontend / vs conventions)
1. No service layer for category/subcategory CRUD — views write models directly, contradicting the "business logic in a service" rule that Expense rows follow.
2. Frontend fetch calls for category/subcategory POST/PUT/DELETE (api.js, subcategories.js) do NOT send the X-CSRFToken header, whereas the project convention (ai/* files) is to include X-CSRFToken from window.wfGetCsrfToken(). This may rely on Django's session-cookie CSRF (SameSite Lax) rather than the header convention — an inconsistency worth verifying.
3. Order field: backend supports order on both category and subcategory, but the frontend never exposes or sends order (always default 0).
4. saveCategory only sends name/icon/color_hex; the backend also accepts order — order is never settable from the UI.
5. Hardcoded user-facing strings in frontend (e.g. 'Name required', 'Category saved ✓', 'Error', 'Deleted') instead of t()/data-i18n, violating the i18n rule.
6. Frontend uses parseFloat for amounts (api.js saveExpense) while the money-handling skill mandates Decimal/never float — a backend/frontend numeric inconsistency (backend stores Decimal).
7. deleteSubcategory in api.js takes a catId param but the deleteSubcategory call in subcategories.js passes (subId, catId); consistent, but api.js signature includes an unused catId in some call paths.

FILES INVOLVED (exact):
- core/models/expenses.py (models)
- core/views/expense_category_views.py (CRUD views)
- core/urls/financial_core_urls.py (routes)
- static/js/expenses/api.js (fetch layer)
- static/js/expenses/categories.js (category UI)
- static/js/expenses/subcategories.js (subcategory UI)
- (related consumers) static/js/expenses/dashboard.js, static/js/budgets/page.js, static/js/import/page.js, static/js/ai/blocks/blocks_form.js

No files were modified. I did not run the test suite or verify CSRF behavior at runtime — those are flagged as items to check, not confirmed.

## Work done

## Files changed (exact state)
- none

## Verification
Overall: NOT VERIFIED - the final checks did not run (the task did not finish).

## Not run / open issues
- Browser E2E, real model quality and anything not listed above as PASSED were not verified by this run.

Tokens (as reported by the provider): in 130650, out 2143
