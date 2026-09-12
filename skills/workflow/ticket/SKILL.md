---
name: ticket
description: "Write a self-contained, agent-ready GitHub issue — one any agent can execute with zero conversation history — then peer-review the body before creating it. Use when the user asks to file an issue, record a bug or task, or plan work to pick up later."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [git, gh]
metadata:
  hermes:
    tags: [contributing, github, issues, planning, workflow]
---

# Ticket — agent-ready GitHub issues

Turn a request into a GitHub issue that a fresh agent can execute without asking a single
clarifying question. The issue body **is** the context — "as discussed" is a defect.

## Step 1 — Understand the ask

Read the request. One task → one issue. A batch directive ("file one per unpark item") → one issue
per task; present the list of titles and confirm before creating.

Repo defaults to `origin`:

```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

If the request starts with `in <owner/repo>`, strip it and target that repo instead — verify it
exists with `gh repo view <owner/repo>`, and pass `-R <owner/repo>` to every `gh` command below so
the issue lands there.

## Step 2 — Gather evidence

An agent picking this up should not have to rediscover facts. Collect them now:

- **File paths** — confirm each exists (`ls`, `test -e`); cite real paths, not guesses.
- **Stale references** — `grep` for the pattern being changed, so the issue can say what else
  moves with it.
- **Current state** — run the repo's own gates to capture ground truth:
  `./scripts/leak-scan.sh .` and `python3 scripts/validate-skills.py .` (record the output,
  including any pre-existing failures — do not silently fix them).
- **Verification commands** — decide, now, which commands will prove the work is done. They must be
  **falsifiable**: they fail if the work is wrong.
- **Repo constraints** — a new skill must be named in `README.md` (`validate-skills.py` enforces
  it) and carry `license:` frontmatter; a new stage must also be added to the stage list in
  `CONTRIBUTING.md`; the leak gate must pass. Put the ones that apply into the issue.
- **Privacy** — issue bodies are public forever. Use the placeholder vocabulary in
  `CONTRIBUTING.md`;
  never paste a real name, handle, host, or health value. Nothing scans GitHub for you.

## Step 3 — Draft the body

Every issue uses this structure. Omit a section only when it is genuinely empty, and say so.

```markdown
## Context

<1–2 sentences: why this exists and what it fixes, for an agent with zero history.>

## Prerequisites

<Access or state needed first. If none beyond a normal checkout: "None beyond a clean checkout.">

## Current State

<What exists now — file paths, command output, grep results. Concrete, no "see discussion".>

## Desired State

<What should exist after. Written so it can be checked against Current State.>

## Not in Scope

<Explicit exclusions — prevents scope creep.>

## How to Verify

<Commands that fail if the work is wrong.>

```bash
./scripts/leak-scan.sh .              # expect: PASS
python3 scripts/validate-skills.py .  # expect: OK
git log -p --all -- . ':(exclude)scripts/leak-patterns.tsv' \
  ':(exclude)scripts/leak-scan.sh' | ./scripts/leak-scan.sh --no-gitleaks -   # expect: PASS
```

## Dependencies

<Other issue numbers that must be closed first, or "None — can start immediately.">
```

Rules: no reference to a conversation; every path exists at time of writing; every verify command
is runnable and deterministic; dependencies cite issue numbers, not descriptions.

## Step 4 — Peer-review the body (gate)

Before creating the issue, run `@peer-review` on the body:

```
You are reviewing a GitHub issue that will be assigned to an AI agent with ZERO history. The body
is the agent's only context.

Issue title: <title>
Issue body: <body>

1. Is every path and command verifiable and correct?
2. Is every claim specific enough to falsify?
3. Is anything assumed that is not written down?
4. Could a competent agent finish this without asking the user anything?
5. What is missing?
```

Do not create the issue until the review passes, or you have documented why you overrode it. Use
your judgement — accept real gaps, reject nitpicks. For a batch, review the first issue fully; for
the rest, check each follows the same structure.

## Step 5 — Create

```bash
gh issue create --title "<title>" --body-file <file> [--label <label>] [-R <owner/repo>]
```

Write the body to a temp file and use `--body-file` — it avoids shell-escaping damage on multi-line
bodies. Add `-R <owner/repo>` only when targeting a repo other than `origin`. Labels are advisory;
use what the repo already has (`gh label list`).

## Step 6 — Report

```
## Issues Created

| # | Title | Depends on |
|---|-------|------------|
| 12 | ... | — |
```

## Anti-patterns

| Don't | Do |
|---|---|
| "Update the docs" | Name the file, the current text, and the replacement |
| Reference the chat ("as we said") | Put the fact in the body |
| "Verify it works" | Give a command and its expected output |
| Skip "Not in Scope" | State what the issue does **not** do |
| Create without peer review | Gate the body first |

## When to use

- The user asks to file an issue, note a bug, or park work.
- Before `@work`, when there is no issue yet.
