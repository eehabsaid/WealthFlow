# WealthFlow Application Architecture & System Design

## 1. Overview
WealthFlow is a modern, web-based personal financial management platform built on Python and Django.
It tracks multi-currency liquid cash, bank balances, high-yield bank certificates, physical gold holdings, real estate, vehicles, other fixed assets, monthly salary income, and recurring expense categories.

## 2. Core Architecture Principles
- **Django Core**: The central application logic resides in the `core` app.
- **Service-Oriented Design**: Business logic, financial math, and AI capabilities are organized into modular services under `core/services/`.
- **Read-Only Context Pipeline**: The AI subsystem operates strictly via a 100% read-only context pipeline (`core/services/ai/context_builder.py`, `orchestrator.py`, `context_builder_service.py`).
- **Data Provider Registry**: Business data signals (balances, certificates, gold, salary, expenses, fixed assets) are accessed via standardized data providers registered in `core/services/ai/providers/`.
- **Provider-Independent AI**: AI orchestration works seamlessly with any provider (Ollama, OpenAI, Claude, Gemini, Azure OpenAI) without vendor lock-in.

## 3. Key Subsystems
1. **Financial Advisor Engine** (`core/services/financial_advisor/`): Aggregates portfolio overview, cash flow, goal planning, risk analysis, spending intelligence, and scenario simulations.
2. **AI Capability & AST Indexer** (`core/services/ai/codebase_indexer.py`, `capability_registry.py`): Indexes codebase architecture and service capabilities dynamically.
3. **System Knowledge Base** (`ai_knowledge/`, `system_knowledge_engine.py`): Permanent system knowledge repository describing schemas, business logic, investigation workflows, and response standards.
