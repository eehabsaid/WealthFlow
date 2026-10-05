"""Per-user AI Advisor settings: which keys a user may own, and the usage-limit keys.

Everything NOT in AI_USER_SETTING_KEYS (permission tier, read-only, multi-agent, Ollama URL, OpenAI base URL,
Azure endpoint, pipeline switches) is sysadmin-only and always resolves to the general (owner=NULL) value.
"""

USE_GENERAL_KEY = "ai_use_general_settings"  # per-user row; "false" = user runs on their own settings
USER_LIMIT_KEY = "ai_monthly_token_limit"  # per-user row, sysadmin-written; 0/empty = use the default
DEFAULT_LIMIT_KEY = "ai_default_monthly_token_limit"  # global row, sysadmin-written; 0/empty = unlimited

AI_USER_SETTING_KEYS = frozenset(
    {
        "ai_enabled",
        "ai_provider",
        "ai_model",
        "ai_temperature",
        "ai_context_size",
        "ai_timeout",
        "ai_system_prompt",
        "ai_max_tokens",
        "ai_top_p",
        "ai_top_k",
        "ai_repeat_penalty",
        "ai_seed",
        "ai_keep_alive",
        "ai_history_window",
        "ai_context_token_budget",
        "ai_openai_model",
        "ai_openai_api_key",
        "ai_claude_model",
        "ai_claude_api_key",
        "ai_gemini_model",
        "ai_gemini_api_key",
    }
)
