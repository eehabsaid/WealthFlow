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
trainer, continuing from the saved Agent2 LoRA adapter at the path configured by `initial_adapter_dir` in
`profiles/recovery.json`. It verifies the adapter's source model, base-model path, and LoRA rank; a missing or incompatible
Agent2 adapter blocks training rather than falling back to the untouched Qwen checkpoint. To run the complete workflow
(validate, export, train, register, evaluate) in order:

```powershell
python manage.py ai_training --profile recovery
```

Agent2-based Recovery artifacts are written to `D:\AI-Models\training\recovery\run-recovery-agent2\`. Any existing
`run-recovery\` outputs are retained separately and are not reused as Agent2-based results.

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

- `models/` AgentTrace (recorded runs)  `migrations/`  `management/commands/ai.training.py` (the one command)
- `services/` (Windows side) recorder, judges, generator, runner, export, inspect_file, preflight, train_stage, ollama_stage, wsl, pipeline, testset, evaluate, eval_report, ollama_ctl
- `trainer/` (runs inside WSL2, no Django) render, train, export_gguf, setup_env.sh  `tests/`  `output/` (git-ignored)

Hook into the app: one call in `ai/views/ai_chat/chat_pipeline/agent_pipeline.py`. Real chats are recorded only if the
sysadmin setting `ai_trace_recording` is true.

## Coding model, from the standalone agent's own history (ledger-based coding_agent)

A second, separate coding fine-tune from the standalone dev agent's own completed work (`coding_agent/tasks/*/ledger.json`), not from git
history (that is the git-history coding fine-tune further up this file, under "Point 10" / `coding_agent/training.json`). Only a task the
agent itself marked finished AND verified becomes a candidate - a failed, stopped, rejected or unverified task never does:

- **qa** - an investigation/read-only question (`status: "answered"`): the goal and the agent's own final answer become a QUESTION/ANSWER example.
- **patch** - an implementation task (`status: "completed"`, final verification `VERIFIED`): the goal, the changed files' content *before* the
  task, and the task's own frozen diff (`ledger.freeze_result_diffs()`, called right when a task completes) become a TASK+FILES/diff example.
  A task completed before this feature existed has no frozen diff and is skipped (`no_source_diff`) - there is nothing reliable to rebuild it
  from after the fact, by design.

Both example types are redacted (secrets/tokens always; emails, phone numbers and currency-looking amounts too, unless `redact_patterns` is
turned off in that type's config), deduplicated (exact and near-duplicate, via `dedup_similarity`), size- and structure-checked, then written
to a **review file you approve by hand** - nothing reaches training on its own:

```
python manage.py ai_training                                    # recovery, agent2, etc. (unchanged)
python scripts/ledger_train.py --stages extract                 # scan coding_agent/tasks, (re)write the two review files
```

This writes `coding_agent/qa_review.jsonl` and `coding_agent/patch_review.jsonl`, one JSON row per candidate task, `"decision": "pending"`.
Open either file, change `"decision"` to `"approved"` or `"rejected"` for each row you've looked at (the full example - prompt and answer/diff
- is right there in the row, under `"example"`), save, and re-run `--stages extract` any time to pick up new tasks without losing your
decisions. A row whose task no longer qualifies (e.g. you deleted it) is dropped automatically and reported.

```
python scripts/ledger_train.py --stages build                   # merge the APPROVED rows of both files into one deterministic split
python scripts/ledger_train.py --stages train                   # train (or --dry-run to only check readiness)
python scripts/ledger_train.py --stages evaluate                # compare the new model with recovery on the held-out approved examples
python scripts/ledger_train.py                                  # all four stages, in order
```

`build` writes `work/coding_agent/coding_agent_train.jsonl` (training) and `coding_agent_heldout.json` (held out, deterministic by task id -
a task is always on the same side, so held-out never leaks into training) plus a `coding_agent_dataset_report.txt` with counts by kind. It
refuses (status stays at `"build"`, train/evaluate are skipped) if nothing has been approved in either file yet.

**Base model and naming** (`coding_agent/coding_agent_training.json`, a complete, standalone settings file - same shape as
`profiles/recovery.json`, not an overlay on `config.json`): this model continues training from **your recovery model's own saved adapter**,
not from scratch and not from the plain `-agent2` model, via `initial_adapter_dir`/`initial_adapter_model`. `original_model` and `best_model`
are both set to `qwen3.8:27b-recovery` (what it continues from, and what `evaluate` compares the new model against), while `new_model` is set
explicitly to `qwen3.8:27b-coding_agent` - a clean name with **no "recovery" in it** - so the model you end up with is `<base>-coding_agent`
regardless of which model happens to be selected in Settings when you run it. **Confirm `initial_adapter_dir` against your own machine before
training** (it should be recovery's own `run_dir_override` + `\out\adapter` - check `profiles/recovery.json`'s own `initial_adapter_dir` for
the pattern); a wrong or missing path blocks training rather than silently falling back to the untouched base. `min_traces`, LoRA
hyperparameters, `eval_min_gain_points` and `eval_max_slower_percent` are also in this file, not the shared `config.json`. The model in
Settings is never switched, by `build`, `train` or `evaluate`.

**Evaluation** scores the two example kinds differently, in one combined run and report (`coding_agent_eval_report.txt` /
`coding_agent_eval_results.json` under `work/coding_agent/`):
- *patch* examples are scored by code, the same way as the git-history coding fine-tune (`scoring.py`): the model's patch is applied to a
  clean worktree and the real Django tests mapped to the changed files (`test_areas` in `coding_agent/config.json`) decide. Unlike the
  git-history dataset, a ledger task is not tied to one commit, so the clean worktree is **git HEAD**, not a parent commit - local,
  uncommitted dev-agent changes are not reproduced in evaluation. Commit a task's changes (after you've reviewed them) before relying on its
  patch example in an evaluation run.
- *qa* examples have no code-checkable ground truth. They get a disclosed text-similarity proxy against the agent's own recorded answer
  (never a correctness judgment) and the new model's full transcripts are written into the report for you to read and judge yourself.
- The **combined verdict is decided by the patch results alone** (gain in tests passing, no new protected-file touch, not meaningfully
  slower) - qa never wins or loses a verdict on its own; if there are no held-out patch examples yet, the run says so plainly instead of
  claiming a win.

**Extraction config vs. training config**: `coding_agent/qa_training.json` and `patch_training.json` only control extraction (system prompt,
size limits, `held_out_every`, dedup, redaction, and - for patch - which paths count as tests, via `test_prefixes`, the same wildcard-prefix
format as the git-history dataset's own `test_prefixes`). The actual model (base, LoRA settings, naming, adapter to continue from, eval
thresholds) lives only in `coding_agent_training.json`.

**Failure modes**: `extract` never fails outright - a task that cannot be read, or does not qualify, is just counted and skipped, with the
reason in the log (`not_answered`, `not_completed`, `not_verified`, `no_source_diff`, `protected_file`, `too_many_files`, `context_too_long`,
`answer_too_long`/`diff_size`, `empty_goal`/`empty_goal_or_answer`, `duplicate_exact`, `duplicate_near`). `build`/`build_combined` refuse with
nothing approved rather than training on an empty set. `train` runs the same WSL preflight checks as the other local models (free disk, WSL
reachable, enough approved examples) and blocks before touching anything if they fail; a missing or mismatched `initial_adapter_dir` blocks
training the same way an Agent2-recovery mismatch does for the recovery profile. `evaluate` with an empty held-out file (nothing approved and
held out yet) reports `"no_tasks"` and says to run `build` first, rather than silently comparing nothing.
