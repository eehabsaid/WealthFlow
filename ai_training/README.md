# ai_training

Everything for teaching the local model how to investigate lives here (one folder, one command):

    python manage.py ai_training

## Isolated Recovery profile

The default profile remains `wealthflow` and continues to read the existing `config.json`, AgentTrace data, and `output/`.
Recovery has its own prepared Q&A dataset, quality report, training run/checkpoints, export paths, and Ollama name:

```powershell
python manage.py ai_training --profile recovery --stages validate
python manage.py ai_training --profile recovery --stages train
python manage.py ai_training --profile recovery --stages register
python manage.py ai_training --profile recovery --stages evaluate
```

`evaluate` compares the configured WealthFlow model with Recovery using WealthFlow's shared frozen benchmark, judges,
scoring, and report formats. The benchmark stays in `output/frozen_testset.json`; Recovery reports are written under
`datasets/recovery/reports/`. `train` validates and exports the prepared dataset if needed, then uses the shared WSL QLoRA
trainer. To run the complete workflow (validate, export, train, register, evaluate) in order:

```powershell
python manage.py ai_training --profile recovery
```

The complete prepared dataset is `datasets/recovery/questions.jsonl`; validation and generated reports are isolated in
`datasets/recovery/reports/`. Recovery-specific paths, hyperparameters, export quantization, and registration names are in
`profiles/recovery.json`. The mirrored `profiles/wealthflow.json` documents the current WealthFlow values; the default
workflow continues to use `config.json` so existing edits and commands retain their behavior.

The Recovery examples support authorized software analysis and recovery. They require approval before executable changes
or irreversible operations and do not provide license-circumvention or unauthorized-modification instructions.

Stages: questions from the live data -> ask the model (twice each) -> judge with code -> files in `output/`
(`agent_traces.jsonl`, `agent_runs.xlsx`, `report.txt`) -> if enough traces are proven: QLoRA training in WSL2 on the original
model -> merged 4-bit GGUF plus its vision projector -> registered in Ollama under the distinct configured name `qwen3.8:27b-agent2`. The configured
base is `qwen3.8:27b-150k`, the previous trained model is `qwen3.8:27b-agent`, and neither existing model is overwritten.
Your model in Settings is never switched.
Safe to stop and start again.

Run stages explicitly when reviewing new data: `python manage.py ai_training --stages collect`, then
`python manage.py ai_training --stages rejudge`, then `python manage.py ai_training --stages train`, and finally
`python manage.py ai_training --stages evaluate`. The evaluation stage asks questions and takes hours; it never trains or
changes the model selected in Settings.

Model test (own run, hours): `python manage.py ai_training --stages evaluate` asks your model and the `-agent` model the SAME fresh test
questions (kinds never used in training: highest, lowest, average, last 5, count in a year), judged by the same code judges. Before each model Ollama
is restarted and one warm-up question is not counted. It writes `output/eval_report.txt`, `eval_runs.xlsx`, `eval_results.json` and NEVER switches
the model (you choose in Settings > AI Advisor). The model name in Settings is put back even after a crash. `--dry-run` only checks readiness.

## Broad training (16 categories, 4 languages)

Questions come from the live app and your data, never from a fixed list: `services/tables.py` (every table the Agent may read: count, total, per currency, last 3,
month total; test kinds: highest, lowest, average, last 5, count in a year) and `services/families/` (net worth and its parts, Cash Flow projection, certificate
principal and interest, bank balances and interest, transfers and currency exchanges, salary/per-diem/rent income and expenses, asset equity and furniture costs,
expense categories and subcategories, month and year comparisons, budgets and goals, numeric what-ifs, explanations with their records, data-quality counts, vague
questions). Relational totals keep amounts in their recorded currency or use the app's base-currency fields/services; uncomparable amounts are skipped.
Training and evaluation families use disjoint keys and frozen test wording is blocked from training. Wording: frames in
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

## Vision export and image smoke test

The base model is a vision-language model. Training keeps its vision layers frozen; export requires both the merged model GGUF
and Unsloth's `mmproj` GGUF, and saves the original model config and processor files under `work/run-agent2/out/vision/`.
Ollama registration imports the model and projector as separate `FROM` layers. This follows Ollama's
[GGUF import format](https://docs.ollama.com/import) and its [projector-layer detection](https://github.com/ollama/ollama/blob/main/server/create.go).
If the projector or processor/config is missing, registration is blocked instead of creating a text-only model.
Registration also checks that the target tag does not already exist and fails closed if Ollama cannot verify that.

After the configured model has been registered, run this PowerShell smoke test with a local image:

```powershell
$imagePath = "C:\path\to\image.png"
$image = [Convert]::ToBase64String([IO.File]::ReadAllBytes($imagePath))
$body = @{
    model = "qwen3.8:27b-agent2"
    stream = $false
    messages = @(@{
        role = "user"
        content = "Describe what is visible in this image."
        images = @($image)
    })
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -ContentType "application/json" -Body $body
```

- `models/` AgentTrace (recorded runs)  `migrations/`  `management/commands/ai_training.py` (the one command)
- `services/` (Windows side) recorder, judges, generator, runner, export, inspect_file, preflight, train_stage, ollama_stage, wsl, pipeline, testset, evaluate, eval_report, ollama_ctl
- `trainer/` (runs inside WSL2, no Django) render, train, export_gguf, setup_env.sh  `tests/`  `output/` (git-ignored)

Hook into the app: one call in `core/views/ai_chat/chat_pipeline/agent_pipeline.py`. Real chats are recorded only if the
sysadmin setting `ai_trace_recording` is true.
