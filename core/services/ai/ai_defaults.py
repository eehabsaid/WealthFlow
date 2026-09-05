"""
Single source of truth for the fallback Ollama model name.

Every place in the codebase that needs a default for the 'ai_model'
AppSettings key must import DEFAULT_OLLAMA_MODEL from here rather than
hardcoding its own string literal. Before this module existed, three
different files independently hardcoded three different, disagreeing
values ("llama3:latest", "llama3.2:latest", "qwen2.5:3b") — none of
which checked whether that model was actually pulled on the user's
machine, which is exactly what caused "model manifest does not exist"
errors when a hardcoded tag wasn't available locally.

This constant is only ever used as a last-resort fallback for a
brand-new install where 'ai_model' has never been set. Once a user has
configured (or the app has auto-detected) a working model, everything
should read that value instead — nothing should ever need to guess.
"""

DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"
