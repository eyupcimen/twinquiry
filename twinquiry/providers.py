"""Local CLI adapters. No API credentials are read or stored by this module."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from .schema import ANSWER, REVIEW
from .session import write_json


def argv_for(provider, executable, model, folder, schema, web=False, skip_permissions=False):
    if not model or model.startswith("-"):
        raise ValueError("Select an explicit model for each provider")
    if provider == "codex":
        return [executable, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                "-s", "read-only", "-c", 'approval_policy="never"',
                "-c", 'web_search="live"' if web else 'web_search="disabled"',
                "-m", model, "--json", "--output-schema", str(folder / "schema.json"),
                "-o", str(folder / "answer.json"), "-"]
    if provider != "claude":
        raise ValueError(f"Unsupported provider: {provider}")
    args = [executable, "-p", "--model", model, "--output-format", "json",
            "--json-schema", json.dumps(schema), "--safe-mode", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--no-chrome", "--no-session-persistence",
            "--permission-prompts", "none", "--tools", "WebSearch,WebFetch" if web else ""]
    if skip_permissions:
        args += ["--dangerously-skip-permissions"]
    else:
        args += ["--permission-mode", "dontAsk"]
        if web:
            args += ["--allowedTools", "WebSearch,WebFetch"]
    return args


def executable_for(provider):
    binary = shutil.which(provider)
    if not binary:
        raise ValueError(f"{provider} is not on PATH. Install and log in first.")
    if os.name == "nt" and Path(binary).suffix.lower() in (".cmd", ".bat", ".ps1"):
        raise ValueError("Use the native CLI executable on Windows; shell command shims are not supported.")
    return binary


def probe(provider):
    binary = executable_for(provider)
    result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=20)
    if result.returncode or not result.stdout.strip():
        raise ValueError(f"Cannot read {provider} version")
    help_result = subprocess.run([binary, "exec", "--help"] if provider == "codex"
                                 else [binary, "--help"], capture_output=True, text=True, timeout=20)
    required = (["--ignore-user-config", "--ephemeral", "--output-schema"] if provider == "codex"
                else ["--safe-mode", "--json-schema", "--permission-prompts", "--tools"])
    missing = [flag for flag in required if flag not in help_result.stdout]
    if help_result.returncode or missing:
        raise ValueError(f"Update {provider}; required CLI flags are missing: {missing}")
    return binary, result.stdout.strip()


def parse(provider, stdout, folder):
    if provider == "codex":
        events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
        if any(not isinstance(e, dict) for e in events):
            raise ValueError("Invalid Codex event stream")
        if any(e.get("type") in ("error", "turn.failed") for e in events):
            raise ValueError("Codex reported a failed turn; see diagnostics")
        done = [e for e in events if e.get("type") == "turn.completed"]
        if not done:
            raise ValueError("Codex did not complete a turn")
        answer = json.loads((folder / "answer.json").read_text(encoding="utf-8"))
        return answer, {"usage": done[-1].get("usage"), "observed_models": []}
    envelope = json.loads(stdout)
    if isinstance(envelope, list):
        results = [e for e in envelope if isinstance(e, dict) and e.get("type") == "result"]
        envelope = results[-1] if results else None
    if (not isinstance(envelope, dict) or envelope.get("type") != "result"
            or envelope.get("subtype") != "success" or envelope.get("is_error", False)):
        raise ValueError("Claude did not complete a successful turn; see diagnostics")
    if envelope.get("permission_denials"):
        raise ValueError("Claude reported denied tools; results cannot be treated as complete")
    if "structured_output" not in envelope:
        raise ValueError("Claude returned no structured output")
    return envelope["structured_output"], {"usage": envelope.get("usage"),
            "observed_models": list(envelope.get("modelUsage", {})),
            "reported_cost_usd": envelope.get("total_cost_usd")}


def stop_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait()


def call(task, prompt, session, settings, timeout):
    provider = task["provider"]
    binary, version = probe(provider)
    attempts = session / "attempts"
    attempts.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=f"{task['stage']}-{provider}-", dir=attempts)).resolve()
    schema = REVIEW if task["stage"] == "review" else ANSWER
    write_json(folder / "schema.json", schema)
    (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
    command = argv_for(provider, binary, settings["models"][provider], folder, schema,
                       settings["web"], settings["claude_skip_permissions"])
    write_json(folder / "command.json", command)
    started = time.monotonic()
    print(f"{provider}: {task['stage']} round={task['round']} diagnostics={folder}", flush=True)
    try:
        # Each call starts in an empty cwd, separate from both session history and project settings.
        with tempfile.TemporaryDirectory(prefix="twinquiry-call-") as cwd:
            options = {"start_new_session": True} if os.name != "nt" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            with (folder / "stdout.txt").open("wb") as out, (folder / "stderr.txt").open("wb") as err:
                with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                      cwd=cwd, **options) as proc:
                    try:
                        proc.communicate(prompt.encode(), timeout=timeout)
                    except (subprocess.TimeoutExpired, KeyboardInterrupt):
                        stop_tree(proc)
                        raise
                    if proc.returncode:
                        raise ValueError(f"{provider} exited {proc.returncode}; see {folder / 'stderr.txt'}")
        response, metadata = parse(provider, (folder / "stdout.txt").read_text(encoding="utf-8"), folder)
        metadata.update(cli_version=version, elapsed_seconds=round(time.monotonic() - started, 3),
                        requested_model=settings["models"][provider], execution="live")
        write_json(folder / "result.json", {"task_id": task["id"], "response": response, "metadata": metadata})
        return response, metadata
    except (ValueError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        write_json(folder / "failure.json", {"error": type(exc).__name__ + ": " + str(exc), "task_id": task["id"]})
        raise


def demo(task):
    if task["stage"] == "review":
        response = {"verdict": "APPROVE", "summary": "Synthetic review for the offline demonstration.",
                    "strengths": ["The example marks its evidence limitations."], "findings": [],
                    "limitations": ["No real model or source verification was used."]}
    else:
        response = {"summary": f"Synthetic {task['provider']} answer.",
                    "analysis": "Compare alternatives using the supplied requirements, then test the main uncertainty.",
                    "claims": [{"claim": "A small experiment can inform the decision.",
                                "evidence": "Illustrative reasoning, not a researched finding.",
                                "source_ids": [], "status": "unverified"}],
                    "open_questions": ["Which tradeoff matters most to the decision maker?"]}
    return response, {"execution": "demo", "observed_models": [], "elapsed_seconds": 0, "usage": None}
