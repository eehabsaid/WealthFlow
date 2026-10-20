# Plan — Fix the AI-generated User Guide (Word)

Goal: make the AI user guide (Word/PDF) **fast, complete and correct**, in **English and Arabic**, in **Ask and Agent** mode.
Split into **three ordered tasks**. Run the targeted tests between tasks; run the full suite + E2E once at the very end.

> This file is the single source of truth. Each task prompt below references it. Do not re-derive the design; implement exactly what is written here.

---

## Verified facts (already confirmed in code — do not re-investigate)

- **Flow (both modes):** view dispatch → `agent_stage` (Agent) or the staged path (Ask) → `inv_loop.investigate` (the tool loop) → `ensure_document` → `compose_document` → `_about_the_app` (fragile YES/NO) → `_guide` (per-screen) **or** `_single` (from tool evidence).
  - Ask entry: [`core/views/ai_chat/ai_chat_core_views/__init__.py`](core/views/ai_chat/ai_chat_core_views/__init__.py:120) — `agent_stage` at line 120, then `try_direct_answer` (134), `should_go_direct` (170), `run_default_pipeline` (198).
  - Agent entry: [`core/views/ai_chat/ai_chat_core_views/agent_stage.py`](core/views/ai_chat/ai_chat_core_views/agent_stage.py:13) → `run_agent_pipeline`.
  - `ensure_document` is called **after** the loop: [`core/views/ai_chat/chat_pipeline/investigate.py`](core/views/ai_chat/chat_pipeline/investigate.py:84) line 99.
- **The bug:** [`compose.py`](core/services/ai/investigation/compose.py:70) `_about_the_app` does `...upper().startswith("YES")`. When the model answers anything else (or the call fails → `""`), it returns **False**, so `compose_document` (line 175) falls to `_single` (line 190), which writes from `out.results` — i.e. the `app_data_models` **DATABASE SCHEMA** tool output. That is why the file lists columns, not UI labels. `_guide` (line 119) never ran.
- **The app already owns a complete guide:** [`compose_sections.py`](core/services/ai/investigation/compose_sections.py:18) `units(user)` builds one unit per live screen (from `app_pages()` + `page_descriptions.json`), each with a `fallback` Markdown built by `_fallback`/`tab_fallback` (lines 66, 79). This is the **model-free English source** (~35,500 chars). It is currently only used as a per-section fallback.
- **Documented text source:** `doc_engine/content/page_descriptions.json` — `{ "route": {"purpose","steps"}, "route::tab-id": {...} }`. Looked up by [`compose_descriptions.py`](core/services/ai/investigation/compose_descriptions.py:56) `page_evidence`.
- **Translation:** [`compose_translate.py`](core/services/ai/investigation/compose_translate.py:134) `translate_markdown` is **sequential, no persistent cache**. Chunking/quality helpers: `split_chunks`, `rejection`, `acceptable`, `target_language`, `uses_latin_script`, `latin_share`, `copied_share`. Logs `[AI-TRANSLATE]`.
- **Quality gate:** [`compose_quality.py`](core/services/ai/investigation/compose_quality.py:95) `sanitize`, `report` (line 151) → `{chapters, repeated_chapters, repeated_sub_headings, part_markers, internals}`. `thin_tabs`, `replace_blocks`, `blocks`, `clean_title`, `norm`.
- **Exports:**
  - [`build.py`](core/services/ai/exports/build.py:36) `document_for` — line 53-55 pops the first **H1** as the title.
  - [`builders/docx.py`](core/services/ai/exports/builders/docx.py:83) line 83 `add_heading(..., level=min(max(block.level,1),4))` — **H1 is supported**; the "no H1" symptom is that guide chapters are `## ` (H2). **No TOC** is emitted.
  - [`builders/pdf.py`](core/services/ai/exports/builders/pdf.py:94) line 94 uses a single `styles["heading"]` for **all** levels (flattens). Needs level-based styles. **No TOC.**
  - [`document.py`](core/services/ai/exports/document.py:105) `parse_markdown` → `Block("heading", text, level=len("#"))`.
- **Domains:** [`domains.py`](core/services/ai/domains.py:11) `BUSINESS`/`APP`, `DATA_TOOLS=("app_data_models","app_data_query","app_computed_figures")`, `app_enabled()`. `no_info()` in [`domain_scope.py`](core/services/ai/domain_scope.py:38).
- **Settings:** `document_budget_s()`, `document_max_tokens(provider)` in [`agent/settings.py`](core/services/ai/agent/settings.py:43).
- **Respond signature:** `finalize_success(cache_mgr, progress_key, conversation, user_msg, user_text, content_str, executed_tool_calls, sources, request, extra, export_target, offer_export)` in [`response_finalizer.py`](core/views/ai_chat/ai_chat_core_views/response_finalizer.py:25).
- **Tests to follow:** `core/tests/ai/investigation/test_compose_guide.py` (GuideProvider, `ASK`), `test_guide_quality.py` (BadModel), `test_guide_matrix.py` (Ask/Agent × EN/AR), `test_compose_translate.py` (TranslatingProvider, `ASK_AR`), `core/tests/ai/test_chat_domains_pipeline.py` (GuideDomainTest). `make_user` in `core/tests/ai/investigation/support.py`.

---

## Global rules (apply to every task)

- **Do not break what works.** Keep `sanitize()` structural (no phrase/word lists). Keep the domain rule.
- **Files ≤ 200 lines.** If a module grows past that, split into a domain subfolder with `__init__.py` re-exports (e.g. `core/services/ai/investigation/guide/`).
- **i18n en/ar/fr/de** for any new user-facing UI text.
- **No new migrations** expected (translation cache is a file/JSON or a plain table only if a model is added — prefer a JSON cache file under `doc_engine/` to avoid migrations).
- **Ignore out-of-scope:** unused `innerColor` in `chart_crosshair/plugin.js`, unwired `nwTrendClass`, dead duplicates in `core/validators/__init__.py`.
- **Tests use a scripted fake provider** (no real Ollama). Run targeted tests while working; full suite + E2E once at the end.
- **Log lines:** `[AI-TIMING]` (per stage) and `[AI-GUIDE-QA]` (final counts). Paste both in the final report.
- **Final report ≤ 15 lines.**

---

## TASK 1 — Sections A + B + E (decision, model-free English guide, export headings/TOC)

### A. Robust guide-vs-report decision (never depend on the fragile YES/NO)
File: [`compose.py`](core/services/ai/investigation/compose.py:70) and a new pre-loop intercept.

1. Replace `_about_the_app` with a **robust classifier** `is_guide_request(provider, user_text, out, deadline) -> bool`:
   - Parse the reply **leniently**: `strip_think`, take the first word, accept `YES`/`NO`/`yes`/`no`/`نعم`/`لا` anywhere in the first 20 chars.
   - On empty/exception/gibberish → **retry once** with a different phrasing and a higher temperature.
   - Log the **RAW** reply: `[AI-GUIDE-QA] classifier raw=<...> decision=<guide|report>`.
   - **Structural fallback (no word/phrase/language lists):** if the classifier is still unclear, decide by structure — the request asks for a **document** (`wants_written_document(user_text)` is True) **AND** the run used **no data-reading tool** (none of `DATA_TOOLS` in `out.steps`) ⇒ **guide**. Otherwise ⇒ report.
2. **Run the decision BEFORE the loop** so a guide request **skips the loop entirely**:
   - Ask mode: intercept in [`ai_chat_core_views/__init__.py`](core/views/ai_chat/ai_chat_core_views/__init__.py:120) right after `agent_stage` (before `try_direct_answer`), when `wants_written_document(user_text)` and the structural rule says guide.
   - Agent mode: intercept in [`agent_stage.py`](core/views/ai_chat/ai_chat_core_views/agent_stage.py:13) before `run_agent_pipeline`.
   - Both call a new `guide_direct(...)` that builds the guide (Section B) and returns `finalize_success(...)` with the guide content + `export_target`/`offer_export` set.
   - Keep `compose_document`'s post-loop path as a safety net (it now uses the robust classifier too).

### B. Model-free English guide (instant, no LLM call)
File: new `core/services/ai/investigation/guide/` package (or extend `compose_sections.py`), re-exported from `__init__.py`.

1. `build_english_guide(user) -> str`:
   - Title (`# `), a short intro, a **Table of Contents** (list of chapter titles), then **one numbered H1 chapter per screen** (admin-only screens only for sysadmin — reuse `units(user)`'s admin filter).
   - Each tab = **H2/H3** with **Purpose / Steps / Notes** from `page_evidence` (documented text).
   - **Never** use schema output, code, file names, snake_case/ENV, dev commands. Run `sanitize()` at the end (keep it).
   - The existing per-screen composer (`_guide`) becomes an **optional enrichment** that can **never remove or shorten** documented content (only add). If it fails or adds nothing, the documented text stands.
2. **No model call** for the English guide. Target: **< 5 s**.

### E. Export headings + TOC (Word and PDF)
Files: [`builders/docx.py`](core/services/ai/exports/builders/docx.py:65), [`builders/pdf.py`](core/services/ai/exports/builders/pdf.py:84), [`build.py`](core/services/ai/exports/build.py:36).

1. Guide chapters must be **H1** (change the guide builder to emit `# ` chapters, `## ` tabs) so `document_for`'s H1-title pop and the heading levels render correctly.
2. **docx:** already supports H1 (line 83). Add a **TOC** field after the title (python-docx `TOC` field / or a static list of H1s). Keep RTL for Arabic.
3. **pdf:** replace the single `styles["heading"]` with **level-based styles** (`heading1..heading4`) sized by `block.level`; add a **TOC** (static list of H1/H2 with page numbers via ReportLab `TableOfContents`, or a simple static list). Keep RTL.
4. Verify lists, numbered steps, and tables still render.

### Task 1 tests (scripted fake provider)
- Classifier answers `"No."`, `""`, `"yes"`, gibberish, and an **exception** → a **guide is still produced** (structural fallback).
- A **guide request never runs the agent loop** (assert `investigate`/loop not called; `out.llm_calls == 0` for English).
- **No model call** for the English guide (assert provider not invoked).
- **Export has H1 + TOC** (parse the produced docx/pdf blocks; assert a level-1 heading and a TOC block exist).
- Ask/Agent × EN matrix (AR covered in Task 2).

**Run:** `python manage.py test core.tests.ai.investigation core.tests.ai.test_chat_domains_pipeline` (plus the new guide tests).

---

## TASK 2 — Sections C + F (translation cache, parallel translation, final quality gate)

### C. Translation cache + parallel translation
File: [`compose_translate.py`](core/services/ai/investigation/compose_translate.py:134).

1. **Persistent cache** keyed by `hash(source_chunk) + language`. Store under `doc_engine/translation_cache.json` (or a small table if a model is preferred — prefer the JSON file to avoid migrations). On hit, skip the LLM call entirely (2nd request instant).
2. **Parallel translation** where the provider allows (thread pool over chunks; keep the deadline and per-chunk retry). Preserve order in the output.
3. Keep the **still-English check** and `[AI-TRANSLATE]` rejection reasons.
4. **Failed chapters** are shown as **translated title + English body, marked** (never dropped).
5. Add a **management command** `pretranslate_guide <language>` that pre-translates all chapters into a language (populates the cache).

### F. Final quality gate on the FINAL file (every combination)
File: [`compose_quality.py`](core/services/ai/investigation/compose_quality.py:151) `report` + a new `gate_final(markdown, language, documented) -> (markdown, report)`.

Check the **final** file for Ask/Agent × EN/AR:
- every screen present **exactly once**;
- no repeated headings/chapters/near-duplicate paragraphs;
- no internals (code, file names, snake_case/ENV, dev commands);
- no part markers `(1/3)`;
- no schema/column names;
- **Arabic chapters really Arabic** (reuse `latin_share`/`copied_share`);
- **English length within 15%** of the documented-text size.
Anything failing is **repaired from the documented text** (reuse `thin_tabs`/`replace_blocks`/`tab_fallback`). Log **one** `[AI-GUIDE-QA]` line with the counts.

### Task 2 tests
- **Arabic served from cache on the 2nd request** (assert provider not called the second time).
- **Parallel translation** produces the same joined output as sequential (order preserved).
- **Quality gate** repairs a bad file (repeated chapter, part marker, English-in-Arabic) and the final `[AI-GUIDE-QA]` counts are zero.
- Ask/Agent × EN/AR **full matrix** passes the gate.

**Run:** `python manage.py test core.tests.ai.investigation core.tests.ai.test_chat_domains_pipeline`.

---

## TASK 3 — Sections D + G (domain rule, performance)

### D. Business-domain rule (keep)
Files: [`domains.py`](core/services/ai/domains.py:11), [`domain_scope.py`](core/services/ai/domain_scope.py:38).
- Guide is **allowed in Business**; **refused with `no_info()` in App-only domain**.
- Confirm the new pre-loop intercept (Task 1) still applies the domain check **before** building the guide.
- Test: `GuideDomainTest` — guide is a business document; the App domain refuses it; with technical info off, the guide uses documented screen text only.

### G. Performance
- **English guide < 5 s** (no model call — measure with `[AI-TIMING]`).
- **Arabic first time < 6 min**, **repeated < 5 s** (cache hit).
- Add/verify `[AI-TIMING]` lines around: decision, English build, translation (per chunk + total), export.

### Task 3 tests + final verification
- Re-run the full matrix (Ask/Agent × EN/AR) and the domain tests.
- **Full suite:** `python manage.py test` (or the project's runner).
- **E2E:** `scripts/run_full_e2e.py` (or `scripts/run_e2e_tests.sh`).
- **Generate EN and AR guides through the real app** and paste the `[AI-TIMING]` and `[AI-GUIDE-QA]` lines into the final report.

---

## Final report format (≤ 15 lines)
1. One line per section A–G: done + key change.
2. `[AI-TIMING]` lines (EN build, AR first, AR repeat).
3. `[AI-GUIDE-QA]` lines (EN + AR, final counts).
4. Test summary: targeted + full suite + E2E pass/fail counts.
