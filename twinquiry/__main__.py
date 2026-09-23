"""python -m twinquiry"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from . import __version__, providers
from .session import accept, create, load, lock, pending, report, write_json


def parser():
    root = argparse.ArgumentParser(description="Twinquiry: independent research and cross-model review")
    root.add_argument("--version", action="version", version=__version__)
    sub = root.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Snapshot a question and optional text sources")
    init.add_argument("session", type=Path)
    init.add_argument("--question", type=Path, required=True)
    init.add_argument("--source", type=Path, action="append", default=[])
    init.add_argument("--rounds", type=int, default=4)
    init.add_argument("--mode", choices=["research", "compare"], default="research")
    init.add_argument("--web", action="store_true", help="Allow live web tools; reduces input comparability")
    run = sub.add_parser("run", help="Run or resume with both local CLIs")
    run.add_argument("session", type=Path)
    run.add_argument("--demo", action="store_true", help="Synthetic offline demonstration; no model calls")
    run.add_argument("--codex-model")
    run.add_argument("--claude-model")
    run.add_argument("--claude-skip-permissions", action="store_true",
                     help="Explicit Claude permission bypass; does not add extra tools")
    run.add_argument("--timeout", type=int, default=600, help="Per-call timeout in seconds")
    run.add_argument("--steps", type=int, default=80, help="Maximum successful calls during this invocation")
    for name in ("next", "status", "report"):
        sub.add_parser(name).add_argument("session", type=Path)
    submit = sub.add_parser("submit", help="Import a manual response to the pending task")
    submit.add_argument("session", type=Path)
    submit.add_argument("--response", type=Path, required=True)
    submit.add_argument("--task-id", required=True, help="ID from next; prevents accidental stale submissions")
    sub.add_parser("doctor", help="Check required CLI flags without making model calls")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            failed = False
            for provider in ("codex", "claude"):
                try:
                    _, version = providers.probe(provider)
                    print(f"{provider}: {version}; required flags available")
                except (ValueError, OSError, subprocess.SubprocessError) as exc:
                    failed = True
                    print(f"{provider}: {exc}")
            print("Authentication, model access, subscription billing and live behavior are not verified by this check.")
            return int(failed)
        folder = args.session.resolve()
        if args.command == "init":
            create(folder, args.question.read_text(encoding="utf-8"), args.source,
                   args.rounds, args.mode, args.web)
            print(f"Created {folder}. Next: python -m twinquiry next {folder}")
            return 0
        with lock(folder):
            dossier, state = load(folder)
            if args.command == "status":
                print(json.dumps({"outcome": state["outcome"], "completed_calls": len(state["history"]),
                                  "settings": state["settings"]}, indent=2))
            elif args.command == "report":
                report(folder, dossier, state)
                print(folder / "report.md")
            elif args.command == "next":
                result = pending(folder, dossier, state)
                print(json.dumps(result[0], indent=2) if result else f"Finished: {state['outcome']}")
                if result:
                    print(folder / "pending-prompt.txt")
            elif args.command == "submit":
                if state["settings"] and state["settings"]["execution"] != "manual":
                    raise ValueError("Cannot mix manual responses with a live/demo session")
                result = pending(folder, dossier, state)
                if not result or result[0]["id"] != args.task_id:
                    raise ValueError("Task ID does not match the pending task")
                state["settings"] = {"execution": "manual"}
                response = json.loads(args.response.read_text(encoding="utf-8"))
                accept(folder, dossier, state, result[0], response,
                       {"execution": "manual", "observed_models": [], "usage": None})
                print(f"Accepted. Status: {state['outcome'] or 'in_progress'}")
            else:
                if args.timeout < 1 or not 1 <= args.steps <= 80:
                    raise ValueError("Timeout must be positive and steps between 1 and 80")
                settings = {"execution": "demo" if args.demo else "live",
                            "models": {"codex": args.codex_model, "claude": args.claude_model},
                            "web": dossier["web"], "claude_skip_permissions": args.claude_skip_permissions}
                if state["settings"] and state["settings"] != settings:
                    raise ValueError("Execution settings changed; repeat original flags or create a new session")
                if not args.demo:
                    if not all(settings["models"].values()):
                        raise ValueError("Live runs require --codex-model and --claude-model")
                    for provider in ("codex", "claude"):
                        providers.probe(provider)
                state["settings"] = settings
                write_json(folder / "state.json", state)
                print(f"Execution={settings['execution']}; max rounds={dossier['rounds']}; max successful calls={args.steps}", flush=True)
                for _ in range(args.steps):
                    result = pending(folder, dossier, state)
                    if result is None:
                        break
                    task, prompt = result
                    response, metadata = providers.demo(task) if args.demo else providers.call(
                        task, prompt, folder, settings, args.timeout)
                    accept(folder, dossier, state, task, response, metadata)
                print(f"Status: {state['outcome'] or 'paused'}. Report: {folder / 'report.md'}")
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Completed responses were saved; no automatic retry.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
