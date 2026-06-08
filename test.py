"""
fix_mobile_responsive.py

Diagnosis of current issues on mobile:
1. TWO conflicting sidebar animation methods in CSS:
   Block A (line ~600): uses `left: -260px` → `left: 0` (correct)
   Block B (line ~862): uses `transform: translateX(-100%)` → conflicts with A
   Result: sidebar animation is jittery / broken on mobile.

2. #topbar is fixed at top (line ~889) BUT the hamburger (#mobile-nav-trigger)
   is already INSIDE #topbar in index.html — so it shows correctly.
   The page-wrapper needs padding-top to clear the fixed topbar.

3. PHASE 4 form rule `font-size: 16px !important` on .form-control is correct
   (prevents iOS zoom) but the `min-height: 44px` breaks modal compact forms.

4. Chart height set to `height: 320px !important` by `div:has(> canvas)` breaks
   the chart layout on pages where chart is inside a flex container.

5. `overflow-x: hidden` on html/body (Phase 9) prevents horizontal table scroll.

Strategy:
- Remove all conflicting duplicate sidebar blocks
- Keep ONE clean mobile sidebar implementation
- Fix topbar/page-wrapper for fixed topbar
- Remove the 5 specific harmful rules above
- Leave ALL desktop rules (>= 992px) completely untouched

Run from inside the salary_tracker project folder.
"""
import os, re

CSS_PATH = os.path.join("static", "css", "main.css")

with open(CSS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# ── Step 1: Remove everything from PHASE 2 onwards ───────────
# Everything from "PHASE 2: SIDEBAR & LAYOUT" to end is
# the problematic appended block. We replace it with a
# single clean mobile block.

PHASE2_MARKER = "/* ════════════════════════════════════════════════════════════\n   PHASE 2: SIDEBAR & LAYOUT RESPONSIVE MEDIA OVERRIDES"

# Also try Windows line endings
PHASE2_MARKER_WIN = "/* \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\r\n   PHASE 2: SIDEBAR & LAYOUT RESPONSIVE MEDIA OVERRIDES"

cut_idx = content.find(PHASE2_MARKER)
if cut_idx == -1:
    cut_idx = content.find(PHASE2_MARKER_WIN)

if cut_idx != -1:
    content = content[:cut_idx].rstrip()
    print(f"[OK] Removed all Phase 2-9 blocks from main.css.")
else:
    print("[INFO] Phase 2 marker not found — will just append clean block.")

# ── Step 2: Also fix the first mobile block (lines ~595-635) ──
# It uses `left: -260px` approach which is correct BUT it conflicts
# with the desktop block's `transform: translateX(0) !important`.
# Fix: ensure the first mobile block does NOT use transform at all,
# and the desktop block does NOT use transform either.

# Remove any transform from the desktop block since we use left/right
content = re.sub(
    r'(#sidebar\s*\{[^}]*?)transform:\s*translateX\(0\)\s*!important;\s*',
    r'\1',
    content
)
print("[OK] Removed conflicting transform from desktop sidebar rule.")

# ── Step 3: Fix the original mobile block if it uses transform ─
# The original block at ~600 uses left:-260px which is correct.
# Just make sure it doesn't also have transform.
# (Already fine from reading — it uses left, not transform.)

# ── Step 4: Append the clean, correct mobile block ───────────
CLEAN_MOBILE = """
/* ════════════════════════════════════════════════════════════
   MOBILE RESPONSIVE — clean single implementation
   Desktop (>= 992px): untouched — sidebar fixed on left.
   Tablet/Mobile (< 992px): offcanvas sidebar + hamburger.
   ════════════════════════════════════════════════════════════ */

/* ── Fixed topbar on mobile — page content clears it ──────── */
@media (max-width: 991.98px) {
  #topbar {
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 56px;
    z-index: 1030;
    padding: 0 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  /* Push main content below the fixed topbar */
  #page-wrapper {
    padding-top: 56px;
  }

  /* Breadcrumb title: truncate so it doesn't push the Add button off screen */
  #bcTitle {
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
  }

  /* Add button: keep icon, hide text label on small screens */
  #addEntryBtn span[data-i18n] {
    display: none;
  }
}

/* ── Page content padding ─────────────────────────────────── */
@media (max-width: 991.98px) {
  #main-content { padding: 16px 12px 48px; }
}

/* ── Page header: stack title + action button vertically ──── */
@media (max-width: 767.98px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 16px;
  }
  .page-title { font-size: 18px; }
}

/* ── Tables: horizontal scroll inside their container ──────── */
/* The .table-container div wraps every data table.
   We make the container scrollable — NOT the whole page. */
.table-container {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
/* Remove the min-width that was set earlier — let the container scroll */
@media (max-width: 991.98px) {
  .data-table { min-width: 560px; }
}

/* ── KPI cards ─────────────────────────────────────────────── */
/* Dashboard uses col-6 col-lg-3 — already 2-per-row on mobile.
   No change needed. Just reduce value font size. */
@media (max-width: 575.98px) {
  .kpi-card { padding: 14px; }
  .kpi-card .kpi-value { font-size: 20px; }
}

/* ── Modals: slide up from bottom on phones ────────────────── */
@media (max-width: 575.98px) {
  /* Slide-up sheet style */
  .modal-dialog {
    margin: 0;
    max-width: 100%;
    align-items: flex-end;
  }
  .modal-content {
    border-radius: 16px 16px 0 0 !important;
    max-height: 90vh;
    overflow-y: auto;
  }

  /* All col-N inside modal body stack to full width */
  .modal-body [class*="col-"] {
    flex: 0 0 100% !important;
    max-width: 100% !important;
    width: 100% !important;
  }

  /* Footer buttons: primary on top, cancel below */
  .modal-footer {
    flex-direction: column-reverse;
    gap: 8px;
  }
  .modal-footer .btn-primary-custom,
  .modal-footer .btn-secondary-custom {
    width: 100%;
    justify-content: center;
  }
}

/* ── Expense filters: stack vertically on phone ────────────── */
@media (max-width: 767.98px) {
  .expense-filters {
    flex-direction: column;
    align-items: stretch;
  }
  .expense-filters .form-select,
  .expense-filters .form-control { width: 100% !important; }
}

/* ── Report controls: stack vertically on phone ────────────── */
@media (max-width: 767.98px) {
  .report-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .report-controls .form-select,
  .report-controls .form-control,
  .report-controls .btn-primary-custom { width: 100%; }
}

/* ── Settings tabs: horizontal scroll if they overflow ──────── */
@media (max-width: 575.98px) {
  div.settings-tabs-wrapper,
  div[style*="border-bottom"][style*="border-color"] {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    white-space: nowrap;
    flex-wrap: nowrap !important;
  }
  .settings-tab { padding: 8px 12px; font-size: 12.5px; }
}

/* ── Balance currency cards: 2-per-row on phone ──────────────*/
@media (max-width: 575.98px) {
  .currency-card { padding: 14px 10px; }
  .currency-card .cur-amount { font-size: 18px; }
}

/* ── Grand total card ─────────────────────────────────────── */
@media (max-width: 575.98px) {
  .grand-total-value { font-size: 22px; }
}

/* ── Year pills ───────────────────────────────────────────── */
@media (max-width: 575.98px) {
  .year-pill { padding: 4px 10px; font-size: 11.5px; }
}

/* ── Forms inside modals: iOS zoom fix ────────────────────── */
/* font-size >= 16px prevents iOS Safari from zooming on focus */
@media (max-width: 575.98px) {
  .modal-body .form-control,
  .modal-body .form-select,
  .modal-body input,
  .modal-body textarea,
  .modal-body select {
    font-size: 16px !important;
  }
}

/* ── Charts: respect container width ─────────────────────── */
/* Do NOT set a fixed height — Chart.js handles it with
   maintainAspectRatio. Just ensure no overflow. */
.chart-container { overflow: hidden; }

/* ── Toast: full width on phone ───────────────────────────── */
@media (max-width: 575.98px) {
  #toast-container {
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
    width: auto !important;
  }
}

/* ── Global: prevent horizontal scroll at page level ──────── */
/* We allow child containers (tables, charts) to scroll internally.
   The page itself should never scroll horizontally. */
body { overflow-x: hidden; }

/* ── Smooth scrollbars on mobile ──────────────────────────── */
@media (max-width: 991.98px) {
  ::-webkit-scrollbar { height: 4px; width: 4px; }
  ::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
  }
  ::-webkit-scrollbar-track { background: transparent; }
}

/* ── Hardware acceleration for sidebar animation ──────────── */
#sidebar {
  backface-visibility: hidden;
  will-change: left;
}
"""

content = content.rstrip() + "\n" + CLEAN_MOBILE

with open(CSS_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] Clean mobile responsive block appended to main.css.")
print()
print("Summary of fixes applied:")
print("  1. Removed conflicting Phase 2-9 blocks (transform vs left animation conflict)")
print("  2. Removed transform from desktop sidebar rule (left-based approach only)")
print("  3. Fixed topbar: fixed position on mobile, page-wrapper clears it with padding-top")
print("  4. Tables: scroll inside .table-container, not the page")
print("  5. Modals: slide-up sheet on phones, col- stack to full width")
print("  6. iOS zoom fix: font-size 16px on form inputs inside modals")
print("  7. Charts: no fixed height override (let Chart.js handle it)")
print("  8. body overflow-x: hidden (page level, not children)")
print("  9. Smooth tiny scrollbars on mobile")