"""After training: save the small add-on (adapter) and the merged, 4-bit model file Ollama can load."""

from __future__ import annotations

import glob
import os


def model_files(out_dir: str) -> list[str]:
    """The model file(s) in out_dir/gguf*: Unsloth may write to `gguf_gguf` (it adds its own suffix). The vision part (mmproj) is not the model."""
    found = glob.glob(os.path.join(out_dir, "gguf*", "**", "*.gguf"), recursive=True)
    return [f for f in found if "mmproj" not in os.path.basename(f).lower() and "bf16" not in os.path.basename(f).lower()]


def save_all(model, tokenizer, out_dir: str, quant: str) -> dict:
    """Writes out_dir/adapter and out_dir/gguf/*.gguf; returns {"adapter": dir, "gguf": file}. The merge needs lots of disk and RAM."""
    adapter = os.path.join(out_dir, "adapter")
    model.save_pretrained(adapter)
    tokenizer.save_pretrained(adapter)
    gguf_dir = os.path.join(out_dir, "gguf")
    model.save_pretrained_gguf(gguf_dir, tokenizer, quantization_method=quant)
    files = model_files(out_dir)
    if not files:
        raise RuntimeError(f"the GGUF export produced no model file under {out_dir}")
    return {"adapter": adapter, "gguf": max(files, key=os.path.getsize)}
