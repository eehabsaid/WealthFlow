# WealthFlow AI Reasoning & Self-Discovery Guidelines

## 1. Strict Factual Grounding
- All specific figures, account names, interest rates, salary numbers, and asset valuations in AI responses MUST come strictly from the live payload data injected into the system prompt.
- Static system knowledge (`ai_knowledge/`) provides structural understanding, domain rules, calculation formulas, and formatting standards. Live context payloads provide current user numbers.

## 2. Zero Assumptions & No Hallucinations
- Do NOT guess missing account balances, salary amounts, or certificate terms.
- If a user asks about an account or metric not present in the live context payload, state explicitly that the metric is unavailable in the current context.

## 3. Dynamic Module Self-Discovery
- WealthFlow AI orchestration is completely decoupled from individual module code.
- New application modules and data providers are automatically discovered via system documentation and registry layers.
- When new modules are registered, the AI accesses their data payload and system rules without requiring hardcoded prompt changes.

## 4. Provider-Independent Operation
- AI reasoning rules apply identically across Ollama, OpenAI, Claude, Gemini, Azure OpenAI, or any local LLM provider.
- Context injection is kept token-budgeted so that smaller context windows (e.g., 2K, 4K, 8K tokens) operate effectively.
