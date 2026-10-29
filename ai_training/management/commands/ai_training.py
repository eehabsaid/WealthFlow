"""ONE command for the whole AI training data job:   python manage.py ai_training

It builds questions from the live data, asks the configured model, judges every run with code, and writes three files to
ai_training/output/: agent_traces.jsonl (only proven traces), agent_runs.xlsx (every run) and report.txt (kept / dropped and why).
Then, if enough traces are proven, it trains the model in WSL2 and registers it in Ollama under a NEW name (your model is never switched).
Safe to stop and start again. Optional: --user NAME, --limit N, --seed N, --fresh, --out FOLDER, --dry-run, --stages collect,train, --min-traces N."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ai_training.services import pipeline, runner


class Command(BaseCommand):
    help = "Record, judge and export Agent-mode training traces (one automatic run)."

    def add_arguments(self, parser):
        parser.add_argument("--user", default="", help="whose data the questions use (default: the first sysadmin)")
        parser.add_argument("--limit", type=int, default=0, help="ask only this many questions (default: all)")
        parser.add_argument("--seed", type=int, default=None, help="repeatable sample when --limit is used")
        parser.add_argument("--fresh", action="store_true", help="ask everything again, even questions already proven")
        parser.add_argument("--attempts", type=int, default=runner.ATTEMPTS, help="times each question is asked (the repeat check needs 2)")
        parser.add_argument("--out", default=pipeline.OUTPUT_DIR, help="folder for the output files")
        parser.add_argument("--dry-run", action="store_true", help="no questions, no training: only check that everything is ready")
        parser.add_argument("--stages", default="collect,train", help="collect = questions + judging, train = train and register the new model")
        parser.add_argument("--min-traces", type=int, default=None, help="proven traces needed before training (default: ai_training/config.json)")

    def handle(self, *args, **options):
        try:
            user = pipeline.pick_user(options["user"])
        except (LookupError, get_user_model().DoesNotExist) as exc:   # no admin at all / unknown username
            raise CommandError(str(exc) or "unknown user") from None
        self.stdout.write(f"Using the data of: {user.username}")
        result = pipeline.run_all(user, limit=options["limit"], seed=options["seed"], fresh=options["fresh"], attempts=options["attempts"],
                                  out_dir=options["out"], log=self.stdout.write, stages=tuple(options["stages"].split(",")),
                                  dry_run=options["dry_run"], min_traces=options["min_traces"])
        self.stdout.write("\n" + result["report"])
        self.stdout.write("Files: " + ", ".join(result["paths"].values()))
