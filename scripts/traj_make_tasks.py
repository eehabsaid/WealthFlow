"""Make (or check) the list of about 100 real tasks for the agent-loop training batch.

    python scripts/traj_make_tasks.py            make scripts/traj_tasks.json (60 questions + 40 small patches, mixed 3 + 2)
    python scripts/traj_make_tasks.py --check    check the existing list against the files as they are now

Every task asks about something that is really in a source file no earlier task used (symbols, line numbers and gaps are read from the code); patches are only
made in files whose checks can reach VERIFIED and never in money, salary, billing or login code. The list is written only when it passes every check.
Nothing is run and no model is called. scripts/traj_run.py runs the list."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import agent_cli  # sets up Django
from ai.dev_agent.core.project import Project
from ai.services.coding.training import traj_tasks

ROOT = Path(agent_cli.ROOT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "scripts" / "traj_tasks.json"), help="the list file (default scripts/traj_tasks.json)")
    ap.add_argument("--seed", type=int, default=traj_tasks.SEED, help="another seed gives another selection")
    ap.add_argument("--check", action="store_true", help="only check the existing list")
    args = ap.parse_args(argv)
    project, out = Project(ROOT), Path(args.out)
    if args.check:
        tasks = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else []
    else:
        tasks = traj_tasks.build(project, seed=args.seed)
    problems = traj_tasks.validate(project, tasks) if tasks else ["there is no task list yet"]
    kinds = Counter(t["kind"] for t in tasks)
    print(f"{len(tasks)} tasks: {kinds['qa']} questions, {kinds['patch']} patches; " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t['template'] for t in tasks).items())))
    for problem in problems:
        print("PROBLEM:", problem)
    if problems:
        return 1
    if not args.check:
        out.write_text(json.dumps(tasks, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
