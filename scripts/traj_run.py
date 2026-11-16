"""Run the real-task batch for agent-loop training: about 100 real tasks, one at a time, each in a throw-away copy of this repo (your files are never changed).

    python scripts/traj_run.py --dry-run          show what would run, change nothing
    python scripts/traj_run.py --count 5          only the next 5 tasks (a good first test)
    python scripts/traj_run.py                    every task that is not done yet; stop with Ctrl+C, run again to continue
    python scripts/traj_run.py --only T012 T040 --redo     run those two again

Every plan is approved automatically (the real command `python -m ai.dev_agent run --yes`), so you are never asked; a protected file or a command that needs approval is
refused, because the agent then has no terminal to ask in. The model is the comparison model of agent_loop_training.json (recovery). The finished task folders land in coding_agent/tasks, where the trajectory extractor
(python scripts/ledger_train.py --mode loop --stages extract) finds them. The list of tasks is scripts/traj_tasks.json (made by scripts/traj_make_tasks.py);
if some of its files were used by your earlier tasks it is made again for your files before the first task runs."""

import argparse
import os
import sys
from pathlib import Path

import agent_cli  # sets up Django
from ai.dev_agent.core.project import Project
from ai.dev_agent.settings.store import Settings
from ai.models import AISetting
from ai.services.coding.training import loop_stage, traj_batch

ROOT = Path(agent_cli.ROOT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", default=str(ROOT / "scripts" / "traj_tasks.json"), help="the task list (default scripts/traj_tasks.json)")
    ap.add_argument("--work", default="", help="folder for the copies and the progress file (default: <work_dir of agent_loop_training.json>/traj_batch)")
    ap.add_argument("--model", default="", help="model to run the tasks with (default: the model of your Settings)")
    ap.add_argument("--count", type=int, default=0, help="run at most this many tasks now (0 = all)")
    ap.add_argument("--start", type=int, default=1, help="start at this position of the list")
    ap.add_argument("--only", nargs="+", default=[], metavar="ID", help="task ids, e.g. --only T012 T040 (PowerShell turns T012,T040 into two words: both ways work)")
    ap.add_argument("--redo", action="store_true", help="run the chosen tasks even if they already ran")
    ap.add_argument("--timeout", type=int, default=traj_batch.DEFAULT_TIMEOUT_S, help="seconds one task may take")
    ap.add_argument("--dry-run", action="store_true", help="only list what would run")
    args = ap.parse_args(argv)
    log = lambda line: print(line, flush=True)  # noqa: E731
    work = Path(args.work or os.path.join(loop_stage.train_config().work_dir, "traj_batch"))
    model = args.model or loop_stage.names(str(AISetting.get("ai_model", "", user=None) or ""))[0]
    try:
        tasks = traj_batch.prepare(Project(ROOT), args.tasks, work, log)
    except ValueError as exc:
        log(str(exc))
        return 1
    only = {x.strip() for part in args.only for x in part.split(",") if x.strip()}
    todo = traj_batch.pick(tasks, traj_batch.load_done(work), args.start, args.count, only, args.redo)
    log(f"Model: {model}   tasks to run: {len(todo)} of {len(tasks)}   work folder: {work}")
    log(traj_batch.context_line(Settings(Project(ROOT)).load()))
    if args.dry_run:
        for task in todo:
            log(f"  {task['id']} {task['kind']:5} {task['goal']}")
        return 0
    if todo:
        from ai.training.services import ollama_ctl

        problem = traj_batch.preflight(model, ollama_ctl.base_url())
        if problem:
            log(problem)
            return 1
    outcome = traj_batch.run(tasks, ROOT, work, model, log=log, timeout=args.timeout, start=args.start, count=args.count, only=only, redo=args.redo)
    log(outcome["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
