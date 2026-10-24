# Hardcode audit: core/services/ai, core/views/ai_chat, exports builders, registry

Scope: word lists, phrase lists, per-language regexes, refusal markers, junk-heading filters, fixed English constants.
"Replaced" = done in this delivery with tests proving the same routing. Everything else is listed, not touched
(replacing it needs a model call on the chat hot path or changes instant answers).

## Replaced in this delivery
| File | What was hardcoded | Replacement |
|---|---|---|
| investigation/doc_path.py | `YES_WORDS` / `NO_WORDS` / `yes_no()` (EN, AR, FR, DE, ES words) | `core/services/ai/protocol.py`: ONE fixed English protocol (YES/NO), lenient on case / markdown / punctuation / `<think>`; anything else = no usable answer (None) and the existing structural evidence rule decides. Raw replies logged at WARNING (`[AI-PROTOCOL]`). |
| investigation/compose.py | the classifier prompt text | `protocol.ABOUT_APP_PROMPT` |
| domain_scope.py | `_NO_INFO` EN/AR text, Arabic-ratio language guess | user-facing refusal read from `static/i18n/<lang>.json` (`ai_scope_*`, domain names = the UI's `ai_domain_*`), language from the existing `language()` |
| exports/builders/code.py | html matcher `\bhtml\b` (any message with the word made a file) | narrowed to `.html`, "html ... file/page/guide/..." and the Arabic equivalents; refusals never get a file at all (structural check in response_finalizer + export view) |
| investigation/compose_translate.py | one-word language answer trusted blindly | confirmed once through the protocol (YES/NO); only an explicit NO drops it |

## Listed, not replaced
| File | What is hardcoded | Risk if replaced | Proposed replacement |
|---|---|---|---|
| exports/intent.py (`_GENERIC`, `_HOW_TO`) | export / download / how-to words in EN/AR/FR/DE | runs on EVERY chat message; a model call there would make instant answers slow | keep; or derive from i18n verbs; never a per-message model call |
| exports/registry + builders (`terms`, `weak_terms`) | per-format words ("word", "ورد", "pdf") | same as above; the format keys/extensions themselves are technical tokens | move the natural-language terms into the locale files |
| exports/builders/guide_html_assets.py `LABELS` | "Contents", "Skip to main content"... for 4 languages | none; used for the HTML, Word and PDF contents title | move to `static/i18n` like the refusals |
| investigation/refusal.py (`_CAPABILITY`, `_NOT_FOUND`, `_ANNOUNCE`) | ~50 refusal / announcement regexes in EN/AR/FR/DE | decides retries in the investigator loop; a wrong replacement re-opens the "I can't access" give-ups | structural: a reply with no tool call and no figures from tools after investigation = give-up; or one protocol question (GIVEUP/OK) only when the answer is short |
| investigation/compose_quality.py | structural only (regex for snake_case, "(1/3)", duplicates); no words | n/a | already structural |
| investigation/compose_title.py | `# WealthFlow user guide` fallback title (fixed English) | the fallback appears only when the model gives no title | take the title from `page_descriptions.json` / i18n |
| query_engine/lexicon*.py, executors/*.py `_TERMS`, labels*.py | per-language domain words and answer labels (EN/AR/FR/DE) | this IS the instant-answer engine (0 LLM calls); removing it slows every simple question | keep; labels could move to the locale files |
| query_engine/timespec.py, slots.py | month / period words, follow-up words | same | same |
| ai_chat_core_views/generation_pipeline.py `_APP_STRUCTURE_TERMS` | English words that route a question to the app-structure tool domain | wrong domain = wrong tools | let the retrieval scorer (`app_knowledge/scoring.py`) decide |
| app_knowledge/scoring.py `_AR_TERMS`, query_terms_fr_de.py | Arabic / FR / DE query expansion terms | retrieval quality | embeddings (already used for business providers) |
| chat_pipeline/understand.py (Arabic terms) | intent words | routing | same as scoring |
| knowledge_engine/conversation_signals.py, user_notes.py | "teach / correction" phrases | learning notes | structural (feedback buttons already exist) |
| tools/salary_answers.py `_LATEST_WORDS` | "last / latest / recent" | one executor | query-engine slot |
| chat_pipeline/agent_pipeline.py `CHITCHAT_MAX_WORDS` | a length threshold, not words | none | keep (structural) |
| exports/builders/pdf.py, docx.py, text.py, xlsx.py (Arabic literals) | format terms in `register(...)` and the `\u0600` script test | none | script test is structural; terms as above |

Not hardcoded language, by design: export format names / extensions (pdf, docx, xlsx...) are technical tokens.
