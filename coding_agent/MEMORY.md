# Coding-agent memory
One dated line per decision or lesson. Add with `python scripts/agent_memory.py add "text"`. Never store secrets.
- 2026-10-31: Cash Flow calculation (`core/services/financial_advisor/cash_flow_forecast_service`) must never change without the owner's approval.
- 2026-10-31: db.sqlite3 is tracked on purpose; read it to check real data, never edit it.
- 2026-10-31: expected answers must come from real data computed by code, never from the model; never loosen what counts as correct without asking.
- 2026-10-31: the owner is non-technical: short plain answers, ask every question at the start, never decide or act without approval.
