import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wealthflow.settings")
import django; django.setup()

from dataclasses import replace
from ai.training.services import evaluate, pipeline
from ai.training.services.config import load

DRY = "--dry-run" in sys.argv
user = pipeline.pick_user("")
cfg = load()
roles = [("agent2", "qwen3.8:27b-recovery"),
         ("coding_agent", "qwen3.8:27b-coding_agent")]   # confirm exact tag with `ollama list`
out = os.path.join(pipeline.OUTPUT_DIR, "eval_coding_vs_recovery")
fn = evaluate.dry if DRY else evaluate.run
kw = {} if DRY else {"out_dir": out}
args = (user, cfg, evaluate.current_model()) + ((out,) if DRY else ())
res = fn(*args, model_roles=roles, benchmark_dir=pipeline.OUTPUT_DIR, **kw)
print(res.get("report", res))