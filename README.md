# Twinquiry

**One question. Two independent answers. A review trail you can inspect.**

Twinquiry runs research and cross-review through your local Claude Code and Codex CLIs. Use it for technical plans, literature questions, product decisions, or comparing how two models approach the same evidence.

[Quick start](#quick-start) · [Türkçe rehber](docs/README.tr.md) · [Protocol](docs/protocol.md) · [Related projects](docs/related-projects.md)

```text
                   Question + source packet
                           /      \
                 Codex draft    Claude draft
                           \      /
                   Independent cross-reviews
                           |
                 Revise when evidence warrants
                           |
             Repeat up to the configured round limit
                           |
             Report + sources + unresolved questions
```

## What it does

- **Independent first answers:** neither draft receives the other model's response.
- **Cross-review:** each model evaluates the other answer against a shared rubric. Provider labels are omitted from review prompts; writing style can still reveal identity.
- **Bounded research:** up to four review rounds by default, with early stopping and explicit unresolved or blocked outcomes.
- **Comparison mode:** preserve the original answers and collect one review from each provider without revising them.
- **Evidence records:** snapshot supplied text sources; distinguish supported claims, inference, and unverified claims.
- **Resumable sessions:** save every validated response; stop on provider errors rather than silently switching models.
- **Manual handoff:** export prompts and import JSON answers without launching a CLI.
- **Optional web tools:** enable current research explicitly. The default is a fixed source packet for more comparable inputs.
- **Offline demo:** try the complete workflow without accounts or model usage.

The first release supports two providers: Claude and Codex. It is a Python command-line application, not a model, hosted service, or skill collection. You can ask a coding assistant to operate the CLI, but no skill installation is required.

## Quick start

Requires **Python 3.10+**. Running from a checkout needs no pip packages.

```bash
git clone https://github.com/eyupcimen/twinquiry.git
cd twinquiry
python3 -m twinquiry init sessions/demo --question examples/question.md --source examples/requirements.md
python3 -m twinquiry run sessions/demo --demo
```

Open `sessions/demo/report.md`. Demo responses are synthetic and clearly marked; they are not a model-quality result. [Example report](examples/demo-report.md).

On Windows use `python` instead of `python3`. A session directory must be new; use a different directory for a new question.

Optional installation in a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
twinquiry --help
```

On Windows activate with `.venv\Scripts\Activate.ps1` in PowerShell. Packaging may download setuptools; the application has no runtime Python dependencies.

## Run real models

Install and authenticate [Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode) and [Claude Code](https://code.claude.com/docs/en/headless) first. Then:

```bash
python3 -m twinquiry doctor
codex login status
claude auth status

python3 -m twinquiry init sessions/my-research --question examples/question.md --source examples/requirements.md --rounds 4
python3 -m twinquiry run sessions/my-research --codex-model gpt-6-astra --claude-model sonnet
```

Model names above are examples, not access guarantees. Select models available to your account. `doctor` checks executables and CLI flags, not authentication or model entitlement. CLI versions evolve; diagnostics record the version used.

**Billing follows your CLI login and selected model.** Twinquiry neither purchases credits nor guarantees that a model is included in your plan. Check subscription access and any extra-usage settings before live runs. Model calls consume usage; four rounds can involve **up to 16 calls**, not four. No model or provider fallback is configured by Twinquiry. Provider-side routing may still happen; requested and observed model information are recorded separately when available.

### Research versus comparison

```bash
# Comparison: original answers plus two cross-reviews, no revisions.
python3 -m twinquiry init sessions/comparison --question examples/question.md --mode compare

# Web research: models may retrieve different sources.
python3 -m twinquiry init sessions/current-topic --question examples/question.md --web
```

Run either session with the same `run` command and explicit model flags. Web mode is useful for fresh information, but it is not a controlled same-evidence benchmark. Prefer collecting excerpts with URLs and retrieval dates into a shared source file when comparing models.

### Pause and resume

```bash
python3 -m twinquiry run sessions/my-research --codex-model gpt-6-astra --claude-model sonnet --steps 1
python3 -m twinquiry status sessions/my-research
python3 -m twinquiry run sessions/my-research --codex-model gpt-6-astra --claude-model sonnet
```

Repeat the original model and permission flags when resuming. Input or model changes require a new session. Errors and timeouts stop the run; completed responses remain saved. Retrying a failed pending call may consume usage again. Default timeout: 600 seconds per call.

### Claude permission preference

To explicitly pass Claude's permission-bypass flag:

```bash
python3 -m twinquiry run sessions/my-research --codex-model gpt-6-astra --claude-model sonnet --claude-skip-permissions
```

This adds `claude --dangerously-skip-permissions`. It does not expand the tool list: Claude receives no tools in packet mode and only `WebSearch,WebFetch` in web mode. It does not change Codex permissions. The default uses `dontAsk` and denies unapproved actions. See [execution boundaries](docs/protocol.md#execution-boundaries).

### Manual mode

```bash
python3 -m twinquiry next sessions/comparison
# Send pending-prompt.txt to the indicated provider. Save its JSON object as response.json.
python3 -m twinquiry submit sessions/comparison --task-id ID_FROM_NEXT --response response.json
```

Repeat `next` and `submit` until finished. IDs prevent accidentally submitting an answer to an old step. Manual authorship and model identity are unverified. Manual, demo, and live responses cannot be mixed in one session.

## Read the result

Each session contains:

| File | Purpose |
| --- | --- |
| `dossier.json` | Frozen question, source contents, rubric and protocol settings |
| `state.json` | Validated answers, reviews, usage metadata and outcome |
| `report.md` | Both final answers, strengths, objections, sources and open questions |
| `pending-prompt.txt` | Prompt for the next task; useful for manual handoff |
| `attempts/` | Per-call commands, stdout, stderr and result/failure diagnostics |

`mutual_approval` means each answer passed the other model's review. It does **not** mean the two answers are identical or factually proven. `unresolved` preserves outstanding objections; `blocked` means a reviewer identified an essential gap. The report deliberately retains both answers instead of hiding disagreement behind an automatic winner.

Source labels and schema checks are mechanical checks. Citation truth, completeness, and model judgments still require evaluation. Elapsed time and raw token usage are run observations, not universal price or quality rankings. See [methodology](docs/protocol.md).

Sessions are local and ignored by Git. Keep private source material out of public commits. The tool sends the question and supplied source text to both selected providers; it does not upload research to GitHub.

## Development

```bash
python3 -m unittest discover -s tests -v
```

Tests use synthetic replies, mocks and temporary subprocesses without model calls. CI runs on Linux, macOS and Windows with Python 3.10 and 3.12. Live adapter compatibility is separate from this test suite; see [validation](docs/validation.md).

## License

MIT. See [LICENSE](LICENSE). Design references and deliberately excluded features are documented in [related projects](docs/related-projects.md).
