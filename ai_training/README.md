# ai_training

Everything for teaching the local model how to investigate lives here (one folder, one command):

    python manage.py ai_training

Stages: questions from the live data -> ask the model (twice each) -> judge with code -> files in `output/`
(`agent_traces.jsonl`, `agent_runs.xlsx`, `report.txt`) -> if enough traces are proven: QLoRA training in WSL2 on the original
model -> merged 4-bit file -> registered in Ollama under a NEW name (`<your model>-agent`). Your model is never switched.
Safe to stop and start again.

Options: `--dry-run` (check everything, ask nothing, train nothing), `--limit N`, `--user NAME`, `--fresh`, `--stages collect,train`, `--min-traces N`.
Settings (paths, training numbers): `config.json`.

- `models/` AgentTrace (recorded runs)  `migrations/`  `management/commands/ai_training.py` (the one command)
- `services/` (Windows side) recorder, judges, generator, runner, export, inspect_file, preflight, train_stage, ollama_stage, wsl, pipeline
- `trainer/` (runs inside WSL2, no Django) render, train, export_gguf, setup_env.sh  `tests/`  `output/` (git-ignored)

Hook into the app: one call in `core/views/ai_chat/chat_pipeline/agent_pipeline.py`. Real chats are recorded only if the
sysadmin setting `ai_trace_recording` is true.
