#!/usr/bin/env bash
# One-time (safe to repeat): a private Python environment with the training tools, inside WSL2.
set -e
VENV="$HOME/ai_training_venv"
[ -f "$VENV/.ready" ] && echo "training environment already prepared" && exit 0
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv venv --python 3.12 "$VENV"
. "$VENV/bin/activate"
# RTX 50-series (Blackwell) needs the CUDA 12.8 build of PyTorch
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install unsloth unsloth_zoo "transformers>=5" trl datasets accelerate peft bitsandbytes flash-linear-attention
touch "$VENV/.ready"
echo "training environment ready"
