---
name: loop
license: MIT
description: "Use when a task needs 2-5 iterations toward a TESTABLE spec (tests pass, build succeeds). Maker-checker with fresh context per round via native Hermes subagents. NOT for exploration or debate — for convergence on a known target."
trigger: Task needs 2-5 iterations toward a testable spec (tests pass, build succeeds). Prior attempts failed and you need fresh context. Must have verifiable convergence criteria.
tags: [iteration, convergence, delegation, subagent]
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [iteration, convergence, delegation, subagent, delegate_task]
---

# Loop — Maker/Checker with Native Subagents

Each iteration = fresh maker subagent, clean context, shared state file. An independent checker (native subagent or manual verification) verifies each round.

> **Privacy / data handling:** Verification is done manually or via a native Hermes `delegate_task` subagent. Prompts and any context you include are sent to the **active model provider** for subagents. **Keep sensitive health data and personal identifiers out of prompts unless the user explicitly agrees** to include them.

## Before you loop — 4-condition test

All must be true (otherwise delegate directly): (1) repeats/complex enough to amortize setup, (2) verification is checkable (tests/lint/build/reviewer vs spec), (3) token budget absorbs retries, (4) you can run/observe outputs.

## State — `.loop-state.json`

```json
{
  "current": "factual state now",
  "desired": "testable definition of done",
  "status": "progressing|stalled|blocked|converged",
  "summary": "what happened, what changed, why (with evidence)",
  "artifacts": ["paths to files touched"],
  "iteration": 1,
  "lessons": ["what to remember"]
}
```

`current` = facts; `desired` = testable with evidence; `status` decided by parent from checker/observations; `summary` includes failures and evidence.

## Parent instructions

### Setup
1. Run 4-condition test. 2. Write `.loop-state.json` (`current`, `desired`, empty `summary/artifacts/lessons`, iteration 0). 3. Create `.loop-history.jsonl`. 4. Set max iterations (default 5) and per-iteration deadline (default 300s).

### Maker phase (each iteration)
Spawn a fresh maker subagent via `delegate_task` with goal including the “Maker instructions” below, context = state file path/contents + minimal necessary task context/file paths (avoid sensitive data unless agreed), and appropriate `toolsets` (e.g. `["terminal","file"]`). After completion, append prior state to `.loop-history.jsonl`, read `.loop-state.json`, note claims.

### Checker phase (independent verification)
Run an independent check — preferred: a fresh `delegate_task` checker subagent (no maker scratchpad), or manual verification.

Checker should verify artifacts against `desired`, run relevant verification commands if applicable, and return `STATUS: converged|not-converged|blocked`, `EVIDENCE: ...`, `GAPS: ...`.

Parent records evidence/gaps in `summary`, maps to `progressing|stalled|blocked|converged`, and applies **clean eval**: detect/revert illegitimate changes to verification criteria (tests/spec/check scripts) before deciding convergence.

### Convergence
`converged` → stop/report. `blocked` → escalate. `stalled` (no meaningful change) → change approach/escalate. `progressing` → next iteration. 3+ iterations without meaningful change → escalate.

## Maker instructions (include in subagent goal)

```text
You are the MAKER in a convergence loop. A separate checker will verify your work.
1. Read the state file (path in context). Restate prior summary before acting.
2. Compare current vs desired; list approaches that FAILED before; pick a substantively different approach.
3. Do the most impactful work to close the gap.
4. Update state: current (facts), summary (tried/changed/failed/remains with evidence), artifacts, lessons, iteration += 1, status "progressing" (checker decides final).
5. Do NOT modify "desired". Record failures as well as successes.
```

## Rules & guards

- Max 5 iterations by default (>10 usually means wrong `desired`). Subagent self-reports are not facts — always verify artifacts/commands.
- **Timeout:** capture diagnostics (`git diff --name-only`, recent activity) into state and retry differently.
- **False progress/stall/regression:** compare artifacts and concrete results (not prose); keep `.loop-history.jsonl`; revert regressions and change approach.
- `desired` must be testable with evidence, not aspirational.

## Loop vs Kanban

Loop = minutes, single session, ephemeral `.loop-state.json` (2–5 iterations). Kanban = durable cross-session work with named workers/crash recovery — macro-iteration.

## References
- `references/hermes-observability-and-delegation.md`
- `references/champion-challenger-loop.md`
- `references/async-rl-iteration-patterns.md`
