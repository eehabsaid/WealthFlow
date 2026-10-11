# WealthFlow AI Work Log

## Current State
- Current feature/task: AI chat copy button feedback investigation completed — confirmed working.
- Important architectural decisions:
  - Django backend with vanilla JS SPA frontend (no build step, no framework).
  - Single-page app: `templates/index.html` shell loads all scripts via partials in strict order.
  - AI chat endpoint: `POST /api/financial-advisor/ai/chat/` (view: `core/views/ai_chat/ai_chat_core_views/generation_pipeline.py::AIChatView`).
  - AI conversations: `GET/POST /api/financial-advisor/ai/conversations/` and `GET/PATCH/DELETE /api/financial-advisor/ai/conversations/<pk>/`.
  - AI progress polling: `GET /api/financial-advisor/ai/progress/`.
  - Multi-provider AI backend via `core/services/ai/providers/` (Ollama, OpenAI-compatible).
  - Chat pipeline: 13 stages in `core/views/ai_chat/chat_pipeline/` (coverage → entity_check → grounding → prefetch → reason → respond → retrieve → runner → tool → trace → understand → validate → workflow).
  - Context orchestration: `core/services/ai/orchestrator.py::AIContextOrchestrator.assemble_context()` builds intent-driven context from 5 sources (live app structure, business data providers, codebase AST index, capability registry, system knowledge manifest).
  - Currency: single source of truth in `core/services/shared/base_currency.py`. Resolution order: user profile → `AppSettings.home_currency` → fallback `EGP`.
  - i18n: 4 language files (`static/i18n/en.json`, `ar.json`, `fr.json`, `de.json`). Frontend uses `window.t(key, fallback)` and `data-i18n` attributes.
  - Middleware chain: `LoginRequiredMiddleware` → `SubscriptionRequiredMiddleware`. Lapsed users blocked from `/api/` except auth/billing/account/settings GET.
  - AI workspace gated by `feature_required("allows_ai_workspace")` decorator and `planAllowsAIWorkspace()` frontend check.
  - Routing: `static/js/app/routing.js` — `routeAllowed()`, `getFirstAllowedRoute()`, `permissionToRoute()`. AI routes: `ai`, `wealthflow-ai`, `financial-advisor`.
  - AI workspace scripts loaded in `templates/partials/scripts/04_ai.html` (38 script tags, strict load order).
  - Shared services MUST NOT be modified: `base_currency.py`, `currency_conversion_service.py`, `base_currency_recalc.py`.
- Known issues: None identified during investigation.

## Completed Work
- Changes made: None (copy feedback confirmed working as-is; no code edits required).
- Files changed: None.
- Tests executed and results:
  - 2026-10-11: `python manage.py test core.tests.ai` — 398 tests passed, 232.181 seconds, OK. (historical run)
  - 2026-10-11: `python manage.py test core.tests.ai.test_ai_ui_live -v 2` — **3 tests passed in 11.802s, OK**. Playwright/Chromium available and working. All three live tests (`test_full_learning_loop`, `test_model_timeout_shows_retrieved_facts_in_the_ui`, `test_thumbs_down_clear_and_reload_state`) completed successfully.

## Pending Work
- Outstanding tasks: None.
- Known risks: None identified.
- Next steps: Await user instructions for feature implementation.

## Rules
- Record only verified facts.
- Update this file after each approved implementation.
- Do not record secrets or credentials.
- Read the current code before relying on historical notes.