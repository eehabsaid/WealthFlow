"""Command-line entry point (testing only in M1): python -m dev_agent plan|run|execute|status|settings|set-key|keys ..."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .core.project import Project
from .engine import report
from .engine.loop import Agent, AgentError
from .ledger import plan as planlib
from .ledger.ledger import Ledger
from .providers.base import ProviderError
from .providers.registry import KEY_OPTIONAL, PROVIDERS, build_provider
from .settings.secrets import SecretsError, SecretStore
from .settings.store import Settings, SettingsError


class ConsoleApprover:
    def ask(self, kind: str, message: str) -> bool:
        if not sys.stdin.isatty():
            print(f"[not approved, no terminal] {message}")
            return False
        return input(f"\nAPPROVAL NEEDED ({kind}): {message}\nApprove? [y/N] ").strip().lower() in ("y", "yes")


def _emit(event: dict) -> None:
    kind = event.get("type")
    if kind == "package":
        print(f"== package {event['id']}: {event['title']}")
    elif kind == "tool":
        print(f"   {'ok ' if event['ok'] else 'ERR'} {event['name']}")
    elif kind == "command":
        print(f"   ran {event['command']} -> {event['status']}")
    elif kind == "verify":
        print(f"   checks ({event['label']}): {event['overall']}")


def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "coding_agent" / "config.json").is_file():
            return folder
    return start


def _agent(project, with_keys: bool = True) -> Agent:
    settings = Settings(project).load()
    secrets = SecretStore(forbid_under=project.root)
    return Agent(project, build_provider(settings, secrets), settings, ConsoleApprover(), _emit)


def _show_plan(ledger: Ledger) -> None:
    d = ledger.data
    print(f"\nTask {ledger.id}: {d['status']}" + (f" - {d['stop_reason']}" if d["stop_reason"] else ""))
    if d.get("answer"):
        print(d["answer"])
    bad = [e for e in d["events"] if e["kind"] == "invalid_reply"]
    if bad and d["status"] == "stopped":
        print(f"Last invalid model reply (also in {ledger.file.name}):\n{bad[-1]['text'][:600]}")
    if d["status"] in ("stopped", "answered"):
        print(f"Report: {ledger.dir / 'report.md'}")
    if d["plan"]:
        print(planlib.summary_text(d["plan"], d["packages"]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dev_agent", description="Standalone autonomous coding agent (M1: command line for testing).")
    parser.add_argument("--root", default=None, help="project folder (default: the folder holding coding_agent/config.json above the current one)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        sub.add_parser(name).add_argument("task")
    sub.add_parser("execute").add_argument("task_id")
    sub.add_parser("status").add_argument("task_id", nargs="?")
    st = sub.add_parser("settings")
    st.add_argument("action", choices=["show", "set"])
    st.add_argument("key", nargs="?")
    st.add_argument("value", nargs="?")
    sub.add_parser("set-key").add_argument("provider", choices=sorted(PROVIDERS))
    sub.add_parser("keys")
    args = parser.parse_args(argv)
    project = Project(Path(args.root).resolve() if args.root else find_root(Path.cwd()))
    try:
        if args.cmd == "settings":
            store = Settings(project)
            data = store.set(args.key, args.value) if args.action == "set" and args.key and args.value is not None else store.load()
            print(f"provider: {data['provider']}  model: {data['model'] or '(not chosen)'}  context: {data['context_window']}  reserve: {data['reserve_tokens']}")
        elif args.cmd == "set-key":
            secrets = SecretStore(forbid_under=project.root)
            print(f"{args.provider} key saved in the {secrets.set(args.provider, getpass.getpass(f'{args.provider} API key (hidden): '))}")
        elif args.cmd == "keys":
            secrets = SecretStore(forbid_under=project.root)
            print(f"credential backend: {secrets.backend}")
            print("(key values are never shown; use set-key to add or replace one)")
            print("providers needing no key: " + ", ".join(sorted(KEY_OPTIONAL)))
        elif args.cmd == "status":
            if args.task_id:
                print(report.build(Ledger.load(project, args.task_id)))
            else:
                for task_id in Ledger.list_ids(project):
                    data = Ledger.load(project, task_id).data
                    print(f"{task_id}  {data['status']}  {data['goal'][:60]}")
        elif args.cmd in ("plan", "run"):
            agent = _agent(project)
            ledger = agent.plan(args.task)
            _show_plan(ledger)
            if ledger.data["status"] == "awaiting_approval":
                if args.cmd == "plan":
                    print(f"\nApprove and run with: python -m dev_agent execute {ledger.id}")
                elif input("\nApprove this plan and execute? [y/N] ").strip().lower() in ("y", "yes"):
                    agent.approve(ledger.id)
                    print(report.write(agent.execute(ledger.id)))
        elif args.cmd == "execute":
            agent = _agent(project)
            ledger = Ledger.load(project, args.task_id)
            if ledger.data["status"] == "awaiting_approval":
                _show_plan(ledger)
                if input("\nApprove this plan and execute? [y/N] ").strip().lower() not in ("y", "yes"):
                    return 1
                agent.approve(args.task_id)
            print(report.write(agent.execute(args.task_id)))
    except (SettingsError, SecretsError, ProviderError, AgentError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
