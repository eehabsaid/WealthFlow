# WealthFlow Application Architecture & System Design

## 1. Overview
WealthFlow is a Django-based single-tenant personal finance platform for tracking multi-currency liquid cash, bank balances, high-yield bank certificates, physical gold, real estate, vehicles, salary income, and expenses. UI is vanilla JS + Bootstrap 5 with dark/light themes. Supports Arabic, English, French, and German (i18n via JSON files).

## 2. Core Architecture Principles
- **Django Core**: All logic in the `core` app.
- **Service-Oriented**: Business logic under `core/services/`. Financial advisor services under `core/services/financial_advisor/`. AI services under `core/services/ai/`.
- **Read-Only AI Pipeline**: AI operates strictly read-only via `context_builder.py`, `orchestrator.py`, `context_builder_service.py`. Never modifies data.
- **Data Provider Registry**: All AI data sourced via providers registered in `core/services/ai/providers/` — one provider per domain (balance, salary, certificates, gold, expenses, fixed assets).
- **Provider-Independent AI**: Works with Ollama (local), OpenAI, Claude, Gemini, Azure OpenAI. Active provider set in `AppSettings`.
- **Local AI**: Primary models are `wealthflow-v*` custom Ollama models (based on qwen3:14b and qwen2.5:3b).

## 3. Key Service Layers
- `core/services/financial_advisor/` — portfolio overview, cash flow, goal planning, risk analysis, spending intelligence, opportunity detection, scenario planning, wealth growth projections.
- `core/services/ai/providers/` — `balance_provider.py`, `salary_provider.py`, `certificates_provider.py`, `gold_provider.py`, `expenses_provider.py`, `fixed_assets_provider.py`.
- `core/services/ai/context_builder_service.py` — assembles token-budgeted system prompt + financial context + knowledge.
- `core/services/ai/knowledge_engine.py` — injects dynamic DB knowledge entries into system prompt.
- `core/services/ai/system_knowledge_engine.py` — loads and keyword-scores `ai_knowledge/` markdown files into system prompt.
- `core/services/ai/orchestrator.py` — multi-step tool-calling investigation loop with live progress streaming.
- `core/services/ai/autonomous_learning_engine.py` — scans app structure and updates KB (triggered manually via AI Platform UI).

## 4. Frontend JS Module Structure
All AI workspace JS under `static/js/ai/`:
- `ai_chat.js` — chat send/receive, streaming progress
- `ai_context_panel.js` — right-hand context panel with KB, prompt library, capabilities cards
- `ai_conversation.js` — conversation list and history
- `ai_platform.js` — AI Platform tab (dataset, models, benchmarks)
- `knowledge_base/` — `kb_state.js`, `kb_render.js`, `kb_events.js` (Knowledge Base modal panel)
- `ai_prompt_library/` — 6 modules for the Prompt Library modal

## 5. Data Flow for a Chat Message
1. User submits query → `AIChatView.post()`
2. `ContextBuilderService.assemble_messages()` → selects relevant financial advisor services by keyword, assembles token-budgeted system prompt with guardrails + knowledge context + financial payload
3. `AIOrchestrator` → calls provider, executes tool calls in a loop (up to 5 steps), streams progress via cache
4. Final response saved to `AIMessage`, returned to frontend