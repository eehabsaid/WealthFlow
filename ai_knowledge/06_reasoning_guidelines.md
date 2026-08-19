# WealthFlow AI Reasoning & Self-Discovery Guidelines

## 1. Strict Factual Grounding
- ALL figures in responses must come from the live financial payload injected into the system prompt.
- `ai_knowledge/` files provide structural rules and formulas only. Never cite them as sources of user figures.
- Dynamic KB entries (from `AIKnowledgeEntry`) provide user preferences and directives — apply them when relevant.

## 2. Zero Hallucination Rules
- Do NOT guess missing balances, rates, certificate terms, or salary amounts.
- Do NOT combine figures across unrelated domains (e.g., do not mix salary data into gold analysis).
- If asked about a metric absent from the live payload: state explicitly it is not in the current context.
- Cross-domain mixing prevention: answer only about the domains present in the query-matched payload.

## 3. Field Correctness
- Expenses: use `amount_egp`, never `amount`.
- Gold: value = weight_grams × (karat/24) × spot_price_per_gram_24k.
- Certificates: interest = principal × annual_rate (as decimal, e.g. 0.225 for 22.5%).
- Net worth: always convert non-home-currency assets using live `ExchangeRate` records.

## 4. Tool-Calling Reasoning
- The orchestrator supports multi-step tool calling (up to 5 steps).
- Each tool call result is appended to the message sequence before the next call.
- Do not repeat a tool call if the result is already in the message history.
- After tool results are available, synthesize into a single final response — do not output intermediate tool results verbatim.

## 5. Dynamic KB Preferences
- Active `AIKnowledgeEntry` records with `is_active=True` are injected into the system prompt.
- Apply `user_preference` category entries as behavioral modifiers (e.g. "User prefers EGP formatting").
- Apply `business_rule` entries as additional calculation constraints.
- If a KB entry contradicts a built-in rule, the KB entry takes precedence (it represents a user override).