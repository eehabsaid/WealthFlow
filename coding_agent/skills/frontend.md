# Frontend
- Vanilla JS, one file per concern under `static/js/<area>/`, <= 200 lines each. No bundler: scripts are loaded in order from `templates/partials/scripts/0N_*.html` (AI workspace = `04_ai.html`). Line order is load order.
- Every changed JS/CSS file needs its `?v=` number bumped in the template that includes it (browsers cache by that number). A new file needs a new `<script>` / `@import` line.
- Text shown to users comes from `_aiT(key, fallback)` / `t(key, fallback)` or `data-i18n` attributes; never hardcode a visible string.
- Escape every inserted value with `_escapeHtml`. Use `fetch` with the `X-CSRFToken` header from `window.wfGetCsrfToken()` for POST/PATCH/DELETE.
- Extension hook for chat bubbles: push a function to `window._aiMessageExtras` (receives `{role, content, toolCalls, messageId}`, returns HTML).
- Checks: `node --check <file>`, `npm run validate`, `npm run format` (ESLint config `config/linting/.eslintrc.json`, htmlhint, stylelint, prettier).
- Arabic is RTL: use logical CSS (`margin-inline-start`, `inset-inline-end`).
