---
name: loop
license: MIT
description: "Use when a task needs 2-5 iterations toward a TESTABLE spec (tests pass, build succeeds). Maker-checker with fresh context per round. NOT for exploration or debate — for convergence on a known target."
trigger: Task needs 2-5 iterations toward a testable spec (tests pass, build succeeds). Prior attempts failed and you need fresh context. Must have verifiable convergence criteria.
tags: [iteration, convergence, delegation]
---

# Loop Skill

Each iteration = fresh subagent, clean context, shared state file. Independent checker verifies each round.

## Before you loop — the 4-condition test

All four must be true. Miss one → just delegate directly, don't loop.
1. **Task repeats or is complex enough** to amortize loop setup cost
2. **Verification is checkable** — a test, linter, build, or independent reviewer can assess artifacts against spec
3. **Token budget absorbs waste** — loops retry, re-read, explore
4. **Agent has tools** to run and observe its own output

## State file — `.loop-state.json`

```json
{
  "current": "factual state now",
  "desired": "testable definition of done",
  "status": "progressing|stalled|blocked|converged",
  "summary": "what happened, what changed, why",
  "artifacts": ["paths to files touched"],
  "iteration": 1,
  "lessons": ["what to remember for next iteration or next run"]
}
```

- `current`: Facts only. "3 tests passing, 2 failing" not "mostly working"
- `desired`: Must be testable with evidence. "All tests pass" not "code is good." Include how convergence will be verified.
- `status`: Determined by parent based on checker output. `progressing` (artifacts changed, closer to desired), `stalled` (no meaningful change), `blocked` (need human), `converged` (done, verified)
- `summary`: Everything the next iteration needs — what worked, what didn't, blocker details, **evidence for claims**
- `artifacts`: Relative paths. Checker verifies these.
- `iteration`: Subagent increments this
- `lessons`: Compounding knowledge — what to remember. Grows across iterations and across runs.

## Parent instructions

### Setup
1. Run the 4-condition test above. If any fail, don't loop.
2. Write `.loop-state.json` with `current`, `desired`, empty summary/artifacts/lessons, iteration 0
3. Create empty `.loop-history.jsonl`
4. Decide max iterations (default 5) and deadline per iteration (default 300s)

### Each iteration — maker phase
1. Spawn maker subagent via `delegate_task`:
   - **goal**: copy the "Maker instructions" section below, then append the specific task
   - **context**: contents of `.loop-state.json` + state file path + any task-specific context
   - **toolsets**: `["terminal", "file"]` for coding, `["web", "file"]` for research, `["file"]` for writing
2. After maker completes:
   - Append previous state to `.loop-history.jsonl` (one JSON per line)
   - Read `.loop-state.json` — note what the maker claims

### Each iteration — checker phase (independent verification)
3. Run independent checker using the skill's script:
   ```bash
   ${HERMES_SKILL_DIR}/scripts/check.sh "<desired>" "<artifact paths>" "<test command>"
   ```
   - Parse the checker's output for STATUS/EVIDENCE/GAPS
   - The checker outputs `converged`, `not-converged`, or `blocked`
   - Map `converged` → stop, `not-converged` → compare with prior artifacts to determine `progressing` or `stalled`, `blocked` → surface to user
   - Record checker's evidence and gaps in the state file's `summary`

   **If checker is unavailable** (script exits 3, no CLI found): parent must manually verify artifacts — read files, run test commands — before continuing. Do not skip verification.

   **Clean eval principle:** The maker's working tree is untrusted. Before checking, detect if the maker modified verification criteria: `git diff HEAD -- <test files, check scripts, spec files>`. If verification-relevant files were modified by the maker, either revert them (`git checkout -- <file>`) or test against the pre-loop snapshot. Distinguish "maker modified existing test criteria" (bad — reject) from "maker added new test scaffolding" (legitimate — allow). Inspired by slime's coding_agent_rl, which evaluates diffs in a *fresh sandbox* because the agent's working environment is untrusted.

4. Compare artifacts against prior iteration — if files unchanged and `current` changed, likely stall evasion
5. Decide: continue / adapt / escalate to user
6. Optionally rewrite `current` or `desired` before next iteration

### Convergence decision (parent's job, informed by checker)
- `converged` (checker confirmed) → stop, report results to user
- `blocked` (checker or parent) → surface blocker to user
- `stalled` (parent: artifacts unchanged from prior iteration) → change approach or escalate
- `progressing` (parent: artifacts changed meaningfully) → spawn next iteration
- 3+ iterations with no meaningful change → stall, escalate

## Maker instructions (subagent prompt)

Copy this into the subagent's goal:

```
You are the MAKER in a convergence loop. You do the work. A separate checker will verify it.

1. Read the state file (path given in context)
2. RESTATE the prior summary in your thinking before acting — understand what was already tried and why it did or didn't work
3. Compare current vs desired. LIST the approaches that FAILED in prior iterations. Pick a gap and approach substantively different from ALL failed attempts.
4. Do the most impactful work to close that gap
5. Update the state file:
   - current: factual new state
   - summary: what you tried, why you chose it, what changed, what FAILED (so the next iteration doesn't repeat it), what's still needed
   - artifacts: files you created or modified
   - lessons: any knowledge worth carrying forward (gotchas, dependencies, what worked)
   - iteration: increment by 1
   - status: leave as "progressing" — the checker will set the real status
6. Do NOT modify "desired"

Record failures — they're as valuable as successes. The checker, not you, decides if the work passes.
```

## Rules
- Max 5 iterations by default. More than 10 = wrong desired state
- If context accumulates across iterations, put it in a separate file, reference from summary
- Subagent self-reports are not verified facts — parent always verifies artifacts

## Failure modes and guards

**Timeout (subagent doesn't return):** Set a deadline before spawning. If delegate_task times out, **capture diagnostic state before recording the timeout**:
   - `git diff --name-only` — what files were touched since loop start
   - Last N tool calls from the subagent's trace (if observable)
   - Any running subprocesses (`ps aux | grep <relevant>`)
   Then record `{status: "timed_out", summary: "timed out after N seconds. Files touched: [...]. Last activity: [...]", artifacts: [<git diff output>]}` in state file. Retry with a simpler task or different approach — append the diagnostic summary to the retry's context so the new attempt knows what was partially done.

**False progress (subagent claims work not done):** Run a concrete verification command after each iteration. Not "read the file" — run the tests, count the lines, diff the output, curl the URL. If verification fails, override status to `stalled` in the state file before next iteration.

**State regression (iteration N undoes N-1):** Append each iteration's state to `.loop-history.jsonl` before overwriting. One JSON object per line. If `current` gets worse (tests going from 4/5 to 2/5), that's regression — revert to the prior state and try a different approach.

**Stall evasion (rephrasing same state):** Compare artifacts, not prose. If no files were created/modified and no commands produced different output, it's stalled regardless of what `current` says.

**Aspirational desired states:** The `desired` field must contain testable criteria with evidence, not aspirations. "Robustness ≥7" requires a peer review score to cite. "Works on 3 task types" requires listing the 3 tasks and their outcomes. If you can't cite evidence for a claim, it doesn't belong in desired.

## Loop vs Kanban — picking the right primitive

Not every iterative task needs a loop. Hermes has **two** delegation+iteration primitives, and they serve different scales:

| | Loop skill (this skill) | Kanban |
|---|---|---|
| Duration | Minutes, single session | Hours to weeks, cross-session |
| State | `.loop-state.json` (file, ephemeral) | `$HERMES_HOME/kanban.db` (SQLite, durable) |
| Workers | Anonymous `delegate_task` children | Named Hermes profiles with persistent memory |
| Observability | Checker script + parent polling | Board queries (`kanban_show`, CLI, dashboard) |
| Crash recovery | Lost if session ends | Survives gateway restarts |
| Maker-checker | External script via `check.sh` | Dispatcher sets outcome (not worker) |
| Best for | Quick iterative refinement, 2-5 rounds | Multi-agent pipelines, research triage, fleet work, durable tasks |

**Use loop when:** Task is <30 min, needs 2-5 fresh-context iterations, and the session will stay alive.

**Use Kanban when:** Task needs to survive across sessions, involves multiple named agents, or requires durable state that survives crashes. Kanban's dispatcher-as-checker pattern eliminates the Ralph Wiggum failure mode at the architecture level.

**Hybrid pattern:** Use loop for the micro-iteration (one Kanban task's implementation) and Kanban for the macro-iteration (task decomposition, handoffs, retry). Each Kanban worker can internally use the loop skill for its own refinement cycles.

## Native observability hooks

Hermes provides hook surfaces that complement the checker script:

- **`subagent_stop`** shell/plugin hook fires after every `delegate_task` child completes. Use it to log iteration outcomes, capture durations, or trigger verification scripts automatically.
- **`post_tool_call`** hook with a `matcher` for terminal/file tools can log every tool call a subagent makes to a file — giving full mid-execution trace without modifying the subagent's prompt.
- **`/agents`** command (TUI: `/tasks`) shows a live subagent tree with kill/pause controls and per-branch cost/token rollups.

These hooks run in both CLI and gateway mode and don't require external CLI agents (command-code, claude) as workarounds.

## Why maker-checker works

The maker is anchored on its own reasoning — it "sees" its output as correct because it built it. The checker breaks that anchor by approaching the same spec with fresh eyes, same information, but without the maker's reasoning path. This is not about the checker having more information. It's about the checker NOT being primed by the construction process. If the checker had the maker's full scratchpad, it would inherit the same blind spots.

## Champion-Challenger Pattern (for recurring output quality)

The maker-checker split catches self-preferential bias but **cannot detect overfitting** — a solution that passes all current tests but fails on unseen inputs. For recurring outputs that should improve over time (cron jobs, report formats, prompt optimization), use the **Champion-Challenger** pattern:

- **Champion** (current best) holds title until a **Challenger** beats it on a **holdout set** (unseen examples) by a defined margin
- **Never promote on the working set** — that's overfitting. Holdout promotion is mandatory
- Stop when holdout plateaus for 2 rounds (local maximum)

See `references/champion-challenger-loop.md` for the full pattern, state file extension, and Feedback Sweep companion.

## Reference
- `references/hermes-observability-and-delegation.md` — Native Hermes solutions for subagent observability, Kanban vs delegate_task, hook system, steer mode, no-agent cron, context engine plugins. Load when designing delegation strategies or choosing between loop/Kanban/shell hooks.
- `references/champion-challenger-loop.md` — Holdout-validation pattern for recurring output quality improvement. Champion vs challenger with unseen test data, promotion margin, local maximum stop condition, Feedback Sweep companion. Adapted from 0xJeff's Hermes Sensei Loop (Jun 2026).
- `references/async-rl-iteration-patterns.md` — Condensed findings from GLM-5/slime/SkyRL research (Jun 2026). Clean eval principle, diagnostic capture at failure boundaries, and documented forced analogies to prevent re-derivation.
