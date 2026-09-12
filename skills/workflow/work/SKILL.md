---
name: work
description: "Execute a GitHub issue end-to-end: fetch, verify prerequisites, do the scope, run the verification commands and the repo gates, peer-review the result, then ship it via @commit → @create-pr. Use when given an issue number to implement."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [git, gh]
metadata:
  hermes:
    tags: [contributing, github, issues, execution, workflow, leak-gate]
---

# Work — execute a GitHub issue

Pick up an issue, confirm it is actionable, do the work, prove it with the issue's own verification
commands plus the repo gates, then ship it. The issue closes only when verification passes — no
shortcuts.

## Step 1 — Fetch and assess

```bash
gh issue view <n> --json number,title,body,state,labels
```

Read `## Context` first — it is your orientation. Extract the section skeleton (`Current State`,
`Desired State`, `Not in Scope`, `How to Verify`, `Dependencies`).

- State `CLOSED` → report and stop.
- Issue does not exist → report and stop.
- Same `-R <owner/repo>` rule as `@ticket` if the issue is not in `origin`.

## Step 2 — Verify before starting

**Dependencies** — for each issue number in `## Dependencies`, confirm it is closed:
`gh issue view <dep> --json state -q .state`. Not closed → stop and report the blocker.

**Prerequisites** — confirm any access or state the issue names.

**Current State claims** — spot-check the ones that drive the work (paths, command output, config
values). If reality differs from the issue, **trust reality** and note the discrepancy; do not stop
for minor drift.

Report:

```
## Prerequisites Check
- Dependencies: ✅ #41 closed / ⛔ #42 open — blocked
- Claims verified: 4/5 ✅, 1 ⚠️ adjusted
```

## Step 3 — Mark in progress (if the repo uses labels)

```bash
gh issue edit <n> --add-label in-progress     # only if the label exists (gh label list)
```

Skip if the repo has no such label — an empty edit is noise.

## Step 4 — Plan

From `## Current State` → `## Desired State`: what changes, in what order, and how you will undo it.
Scan `## Not in Scope` and stay inside it. If Desired State is unclear after verification, pause and
report — do not guess intent.

## Step 5 — Execute

Smallest change that reaches Desired State. If you hit something major (a core assumption is wrong,
an external blocker), pause and report rather than pushing through. If you think an excluded item
should be included, say so — do not decide it yourself.

Work happens on a branch; `@create-pr` handles branching without moving `HEAD`.

## Step 6 — Verify

Run **every** command in the issue's `## How to Verify`, then the repo gates. A verification command
must be falsifiable — if it cannot fail, it is not a check.

```bash
./scripts/leak-scan.sh .              # expect: PASS
python3 scripts/validate-skills.py .  # expect: OK (only if skills/** changed)
```

If a verify command is genuinely stale or wrong, find a replacement that is **at least as strict**,
and document the discrepancy. You may not relax a check to make it pass.

The complete pre-push gate set — the diff check plus the five checks in `AGENTS.md` ("Pre-push
checks") — runs in `@create-pr` Step 2, so Step 8 is not optional. Note that a tree `PASS` carrying
`gitleaks not found — secrets pass SKIPPED` is **not** a clean secrets result; surface it.

Report:

```
## Verification
- [x] <issue command> → <result>
- [x] ./scripts/leak-scan.sh . → PASS
```

## Step 7 — Peer-review the delivered work (gate)

Run `@peer-review` before shipping:

```
You are reviewing completed work on a GitHub issue. The agent claims it is correct and complete.
Issue: #<n> — <title>
Changes: <files changed / commands run>
Verification: <paste Step 6 results>
1. Is the change correct and complete? 2. Anything changed that shouldn't have been?
3. Anything missed? 4. New risks (security, data, cost)? 5. Anything needing a restart/redeploy?
```

No blocking findings → ship. Blocking findings → fix, re-run Step 6, re-review **once**. Still
blocked → surface to the user. Maximum one re-review cycle; after that the issue needs a human.

Two rules make this a real gate rather than a formality:

- **`@peer-review` runs in a separate context** — a different CLI model, or a subagent (which may be
  the same model: a second *context*, not a second *model*). Hand it the artifacts and the diff, not
  your own summary of them; the separation is the point.
- **Judge objections on evidence, not tone.** A finding backed by a file, a command, or a specific
  mechanism is blocking. A finding that is merely asserted can be answered with your verified facts.
  Do not wave away an evidenced objection because you ran the review.

## Step 8 — Ship

```bash
@commit        # leak-gated commits
@create-pr     # pushes a branch, opens the PR — HEAD does not move
```

Put `Fixes #<n>` in the PR body (the `create-pr` template's Summary) so merging closes the issue.

**If there is no PR to open** (docs-only, or the issue asks for no code change), run the full
pre-push gate set from `@create-pr` Step 2 yourself — the diff check plus the five checks in
`AGENTS.md` ("Pre-push checks") — before finishing. Those gates live in
`@create-pr`; skipping the PR does not skip them. State explicitly that no PR was opened, and why.

## Step 9 — Close and report

If the PR body carries `Fixes #<n>`, the **merge closes the issue** — do not close it by hand before
then, and never while CI is red. Close manually only when no PR will close it, and only after the
user confirms the work is accepted.

```bash
gh issue close <n>     # only when no PR will close it
```

```
## Issue #<n> Complete
**Scope**: <what was done>
**Verification**: <N>/<N> passed
**PR**: <url>
**Peer review**: <main insight and how it was addressed>
```

## Error handling

| Condition | Action |
|---|---|
| Issue closed or missing | Report and stop. |
| Dependency open | Report the blocker and stop. |
| Verification fails | Fix and re-run. If unfixable, revert the branch, report, leave the issue open. |
| Peer review finds a real issue | Fix, re-verify, re-review once. |
| Major surprise mid-execution | Pause, revert if needed, report. Do not force completion. |

## Anti-patterns

| Don't | Do |
|---|---|
| Follow a stale issue blindly | Verify claims; trust reality; note the drift |
| Skip verification | Run every check the issue names, plus the gates |
| Ship without peer review | Review is the acceptance gate |
| Accept all peer feedback | Use judgement — push back with evidence on wrong feedback |
| Partially complete, then close | Reach Desired State and verify, or leave the issue open |

## When to use

- Given an issue number to implement.
- After `@ticket`, when the issue is ready to execute.
