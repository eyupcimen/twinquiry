# Validation record

Date: September 23, 2026

## Automated checks

- 25 standard-library tests pass locally on macOS with Python 3.12.5.
- Tests cover independent initial contexts, round caps, unresolved/blocked outcomes, resume behavior, source snapshot integrity, stale manual submissions, locking, permission argument construction, failed/incomplete CLI results, fake subprocess transport, timeout termination, and demo/live separation.
- The offline demonstration completes end to end and writes a report.
- A clean virtual environment builds and installs the package; the installed `twinquiry --version` and `--help` entry points work.
- CI is configured for Linux, macOS, and Windows on Python 3.10 and 3.12. Check the repository Actions results for the current commit.

## CLI preflight

Required flags were present in Codex CLI 0.154.0-alpha.6.2 and Claude Code 2.1.280. Preflight does not prove model availability or account billing behavior.

## Live packet-mode check

A complete comparison run used the bundled fictional documentation question and requirements: two independent drafts followed by both cross-reviews. All four provider calls returned valid results and the report was written. The outcome was `unresolved`; outstanding objections were retained rather than converted to approval.

- Requested Codex model: `gpt-6-astra`. The CLI result did not expose an observed model identifier, so that identity remains unverified.
- Requested Claude model: `sonnet`. Responses reported `claude-sonnet-5`.
- Claude was invoked with the explicit `--claude-skip-permissions` option and an empty tool list.
- No web tools were enabled. This is a transport and protocol smoke test, not a model benchmark.
- Session transcripts and local diagnostics are excluded from the public repository.

## Scope

Automated tests do not use real models or consume model usage. Synthetic demonstrations are not research findings. No test establishes comparative model quality, source truth, or guaranteed improvement over a single model. Web-tool behavior and native Windows live CLI execution need separate validation.
