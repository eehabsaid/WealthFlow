# ai_training

Everything for teaching the local model how to investigate lives here (one folder, one command):

    python manage.py ai_training

Stages: questions from the live data -> ask the model (twice each) -> judge with code -> files in `output/`
(`agent_traces.jsonl`, `agent_runs.xlsx`, `report.txt`) -> if enough traces are proven: QLoRA training in WSL2 on the original
model -> merged 4-bit file -> registered in Ollama under a NEW name (`<your model>-agent`). Your model is never switched.
Safe to stop and start again.

Model test (own run, hours): `python manage.py ai_training --stages evaluate` asks your model and the `-agent` model the SAME fresh test
questions (kinds never used in training: highest, lowest, average, last 5, count in a year), judged by the same code judges. Before each model Ollama
is restarted and one warm-up question is not counted. It writes `output/eval_report.txt`, `eval_runs.xlsx`, `eval_results.json` and NEVER switches
the model (you choose in Settings > AI Advisor). The model name in Settings is put back even after a crash. `--dry-run` only checks readiness.

## Broad training (16 categories, 4 languages)

Questions come from the live app and your data, never from a fixed list: `services/tables.py` (every table the Agent may read: count, total, per currency, last 3,
month total; test kinds: highest, lowest, average, last 5, count in a year) and `services/families/` (net worth and its parts, cash projection from the Cash Flow
calculator, expenses by category / subcategory, month and year comparisons and shares, salary against expenses, savings, assets with acquisition costs and
renovations, mortgages, budgets, goals, numeric what-ifs, explanations with their records, data-quality counts, vague questions). Wording: frames in
`services/frames_en|ar|fr|de.py`, every noun from the app's own translation files (`phrasing.py`); a label the app cannot translate gives no question.
`taxonomy.py` maps tables to the 16 categories and lists what the app cannot do (no reconciliation function, no general debts/installments module, no
income table besides salary/per diem/rent, no anomaly screen). Near-duplicate wording is removed. Each case carries category, language, level and judge.

Judges (code only): figures from real rows, tool use, no leaked reasoning, language (Arabic by script; French/German/English by the app's own translation
words, French/German answers must be CONFIRMED), and for vague questions the "clarify" judge (answer asks a question and states no figure of its own).
Not provable by code: the quality of explanations and what-if reasoning, whether a clarifying question is a good one, anomalies the model did not mention.

Second model: trained from the ORIGINAL base model, registered as `<base>-agent2` (config `model_suffix`); the first `-agent` model is never touched
(`previous_suffixes`), training files go to `work/run-agent2`. `ai_model` is never switched. Old proven traces are kept and new ones added.

Frozen test: `output/frozen_testset.json` (question wording only; delete it to freeze a new one). Questions never appear in training (own kinds + wording blocked).
Figures are recomputed from live data every run. `--stages evaluate` tests original, current best (`-agent`, if in Ollama) and new on the same questions and
reports accuracy by category, tool-use correctness, hallucinations, language consistency, regressions and timing.

Privacy: everything stays on your PC. `output/` is git-ignored; reports and logs contain counts only (no figures); the dataset and the Excel files hold your real
wording and figures, so never share them.

Options: `--dry-run` (check everything, ask nothing, train nothing), `--limit N`, `--user NAME`, `--fresh`, `--stages collect,train`, `--min-traces N`.
Settings (paths, training numbers): `config.json`.

- `models/` AgentTrace (recorded runs)  `migrations/`  `management/commands/ai_training.py` (the one command)
- `services/` (Windows side) recorder, judges, generator, runner, export, inspect_file, preflight, train_stage, ollama_stage, wsl, pipeline, testset, evaluate, eval_report, ollama_ctl
- `trainer/` (runs inside WSL2, no Django) render, train, export_gguf, setup_env.sh  `tests/`  `output/` (git-ignored)

Hook into the app: one call in `core/views/ai_chat/chat_pipeline/agent_pipeline.py`. Real chats are recorded only if the
sysadmin setting `ai_trace_recording` is true.
