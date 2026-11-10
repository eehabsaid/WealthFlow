# core/ai_pack - the WealthFlow pack for the AI app

`ai/` is a portable Django app and never imports `core`. Everything finance-specific lives here and plugs in through
`settings.AI_PACKS = ["core.ai_pack"]` (see `ai/INSTALL.md`, `ai/packs/__init__.py`).

| Folder | What it adds to ai/ |
|---|---|
| providers/, executors/ | data providers and instant-answer (query engine) executors for expenses, salary, balance, budgets, assets, certificates, market |
| tools/, actions/ | scenario / what-if tools, confirm-card actions (expense, income, reminder, chart), tool validation rules |
| knowledge/, insights/ | data-flow knowledge file, live-data slice, AI insights |
| training_families/ | business training families (income, assets, banking, budget, overview, what-if) |
| agents/ | the advisor agent |
| host.py | answers to the `AI_*` host hooks (sysadmin, permissions, audit, plan gate, currency) |
| pack.py | `register(registry)`: wires all of the above |

Read-only finance tools were moved unchanged. Tests that need WealthFlow data live in `core/tests/ai_pack/`.
