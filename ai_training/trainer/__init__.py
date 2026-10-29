"""Runs INSIDE WSL2 (Linux, GPU). Plain Python: no Django imports. The Windows side (ai_training/services) prepares the files
and starts these scripts; see render.py (text + masks), train.py (QLoRA), export_gguf.py (merge + 4-bit file), setup_env.sh."""
