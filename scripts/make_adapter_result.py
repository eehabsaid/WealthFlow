"""Write out/result.json for a finished training run whose result.json is missing (needed when a later stage continues from its adapter).

    python scripts/make_adapter_result.py D:\\AI-Models\\training\\work\\run-coding_agent

Only writes when out/adapter/adapter_config.json and adapter weights exist, the run's run_config.json exists, and the adapter's
base model matches that run's base_model_dir. An existing result.json is never overwritten."""

from __future__ import annotations

import json
import os
import sys


def norm(path) -> str:
    return os.path.normpath(str(path)).replace("\\", "/").rstrip("/").casefold()


def main(run_dir: str) -> int:
    out_dir = os.path.join(run_dir, "out")
    adapter = os.path.join(out_dir, "adapter")
    result_path = os.path.join(out_dir, "result.json")
    if os.path.isfile(result_path):
        print(f"result.json already exists, left untouched: {result_path}")
        return 0
    config_path = os.path.join(adapter, "adapter_config.json")
    weights = [os.path.join(adapter, n) for n in ("adapter_model.safetensors", "adapter_model.bin")]
    if not os.path.isfile(config_path) or not any(os.path.isfile(w) for w in weights):
        print(f"No complete adapter found in {adapter}")
        return 1
    run_config_path = os.path.join(run_dir, "run_config.json")
    if not os.path.isfile(run_config_path):
        print(f"Missing {run_config_path}")
        return 1
    with open(config_path, encoding="utf-8") as fh:
        adapter_cfg = json.load(fh)
    with open(run_config_path, encoding="utf-8") as fh:
        run_cfg = json.load(fh)
    if adapter_cfg.get("base_model_name_or_path") and norm(adapter_cfg["base_model_name_or_path"]) != norm(run_cfg.get("base_model_dir", "")):
        print(f"Adapter base {adapter_cfg['base_model_name_or_path']!r} differs from the run's base_model_dir {run_cfg.get('base_model_dir')!r}; not writing.")
        return 1
    summary = {"adapter": adapter, "initial_adapter_dir": run_cfg.get("initial_adapter_dir", ""),
               "initial_adapter_model": run_cfg.get("initial_adapter_model", ""), "reconstructed": True}
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=4)
    print(f"Wrote {result_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
