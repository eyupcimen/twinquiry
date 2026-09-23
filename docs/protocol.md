# Protocol and limitations

## Stages

1. Snapshot the question and UTF-8 source documents. Stable IDs S1, S2, etc. identify the packet.
2. Each provider independently produces a structured draft with the same question, sources, and rubric.
3. Each provider receives the other candidate answer for review, without an added provider label.
4. If either review is BLOCKED, stop after collecting both reviews. If both APPROVE, stop with mutual approval.
5. Otherwise, in research mode, each author revises its own answer using its peer's review, explaining accepted changes and reasoned rejections.
6. Repeat cross-review until the round limit. The last step is a review; an unreviewed revision is never presented as approved.

A round contains **two reviews**, one in each direction. At most R rounds cost 2 initial drafts + 2R reviews + 2(R−1) revisions = **4R calls**. With the default R=4 the upper bound is 16 successful calls. Compare mode stops after the two initial answers and two reviews (4 calls). Failures and user-initiated retries can incur additional usage.

The two initial calls run sequentially but remain context-independent: neither prompt contains the other answer, and each CLI call starts in a fresh temporary working directory. Twinquiry does not use persistent conversation sessions. It supplies relevant artifacts explicitly on each step. This makes handoffs inspectable at the cost of repeated context.

## What comparison means

The shared rubric covers correctness, source support, coverage, counterarguments, and actionable conclusions. A reviewer reports strengths, concrete objections, and limitations. Twinquiry displays both candidates and both critiques rather than manufacturing a score or automatic winner.

Removing explicit model labels can reduce an obvious cue, but two-provider review is not fully double-blind. Style, content, and prior knowledge can reveal identity. Reciprocal reviews are not independent ground-truth judgments. Mutual approval of two answers is not semantic consensus.

For meaningful model selection, use multiple representative questions, a fixed packet, repeated trials, and a human or externally validated reference. Compare total effort including reviews and retries. Provider usage counters have different semantics; no dollar savings are inferred from them.

Web research intentionally relaxes input control. Models may find different pages at different times. URLs supplied by models are not independently fetched or verified by the coordinator. For an auditable comparison, collect the relevant text and provenance in the shared packet before initialization.

## State and failures

`state.json` records successful validated responses using atomic replacement. A lock prevents two normal processes from advancing the same session concurrently. If a process is forcibly terminated, inspect whether it is still running before deleting a stale `.lock`.

A hash binds the session to its question, source snapshot, mode, round cap and web setting. Changes require a new session. This is an accidental-change guard, not tamper-proof storage: someone with file write access can edit both files.

Every manual response must match the current task ID. Live runs require a zero process exit, a successful completion envelope, a schema-valid response, and consistent verdict fields. Empty responses, failed turns, Claude tool denials and timeouts are errors. Twinquiry does not silently retry or fall back to another model.

A crash after a provider completed but before state persistence can cause that pending task to be rerun and charged again. Inspect per-attempt `result.json` before deciding to retry. No automatic paid recovery is performed.

## Execution boundaries

- Codex runs with a read-only shell sandbox, noninteractive approvals, ignored user configuration, and a fresh empty working directory. It does not receive the target project's working directory. Authentication still follows the CLI's credential handling. Organization-managed policy and provider built-ins can still apply.
- Claude runs in safe mode, with a strict empty MCP configuration and no persistent session. Packet mode exposes no tools; web mode exposes only WebSearch and WebFetch.
- `--claude-skip-permissions` explicitly passes the requested bypass flag while retaining that narrow tool list. It is never enabled implicitly.
- A working directory and read-only shell are not a complete filesystem privacy boundary. These CLIs authenticate and may write their own metadata outside the working directory. For untrusted workloads, use an externally isolated environment.
- Prompt-injection resistance is not guaranteed. Source documents and candidate answers are treated as evidence in protocol prompts, but model obedience is not a security boundary.
- Twinquiry calls no API SDK and stores no login tokens. It invokes local CLIs using an argument list and stdin, without a shell. Existing environment authentication can affect billing. Inspect it through supported provider tools.

The application creates research artifacts only. It has no code-building, commit, push, publishing, or arbitrary command-template feature. Native CLI binaries are required for live Windows use; batch/PowerShell npm shims are rejected.
