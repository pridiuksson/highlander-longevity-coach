---
name: commit
description: "Create well-scoped conventional commits from the current changes — leak-gated, including the commit message. Use when the user asks to commit, stage, or 'wrap this up', and as the commit step of the @work → @commit → @create-pr ship gate. A red leak gate means stop."
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [git]
metadata:
  hermes:
    tags: [contributing, git, commits, workflow, leak-gate]
---

# Commit — leak-gated conventional commits

Turn the session's changes into small, readable commits, each with one reason. This skill is the
commit half of the ship gate; `create-pr` is the other half.

**The one rule that overrides everything below:** the leak gate must pass over the tree **and** the
commit message before you commit. A red gate means **stop** — do not commit, do not "fix it next
commit", do not stage around it. See `CONTRIBUTING.md`.

## Step 1 — Gather

Start from what is actually on disk; the session memory tells you *why*.

```bash
git status --short
git diff HEAD
git diff --cached
```

Reconcile the two sources. If the session says a file changed but `git status` does not show it,
the edit was not saved — ask the user to save, then re-run.

No changes → report "Nothing to commit" and stop.

## Step 2 — Plan the commits

Split by **independent intent**, not by file type. The test is revertability: if two changes must
be reverted together, they belong in one commit.

| Situation | Split? |
|---|---|
| Skill edit + the `README.md` / `CONTRIBUTING.md` mention it requires | **No** — the validator forces them together |
| Skill edit + an unrelated fix in another skill | **Yes** |
| Profile template + a doc that describes it | **No** |
| Several skills changed for one reason each | **Per skill** |
| Docs rewritten for one purpose | **No** |

Messages are conventional commits with a mandatory type:

```
<type>: <imperative description of why>
```

| Type | Use for |
|------|---------|
| `feat` | New skill or new capability |
| `fix` | A bug in a skill, script, or doc |
| `refactor` | Behaviour-preserving rewrite |
| `docs` | README / ONBOARDING / CONTRIBUTING / reference docs |
| `test` | Test files only |
| `chore` | Config, CI, gitignore |
| `style` | Formatting only |

History also contains a non-standard `peer-review:` type. Use the standard set going forward; map
those commits to `refactor` or `docs`. Do **not** rewrite history to fix them.

Message rules:

- Imperative mood — "add leak gate to commit flow", not "added".
- Say **why**, not only what — "fix dangling reference after rename", not "edit skill".
- Subject under 72 characters; add a body when the reason is not obvious from the subject.
- **No attribution lines** — no co-author, no "Generated with", no tool signatures.

## Step 3 — Blocking checks

Run every check over the **final** planned content. Any failure stops the commit.

| # | Check | Command | On failure |
|---|-------|---------|------------|
| 1 | Whitespace / conflict markers | `git diff HEAD --check` | Report the lines, stop. |
| 2 | Pre-staged by another session | `git diff --cached --name-only` | If a path is staged but you did **not** touch it this session, list it and stop — another agent's work is in the index. |
| 3 | **Leak gate — tree (required)** | `./scripts/leak-scan.sh .` | See exit codes below. Red → stop. |
| 4 | Skill structure | `python3 scripts/validate-skills.py .` | Only when a `skills/**` file changed. A missing README mention is fixed by adding it (see note); any other problem → stop. |

**Adding a new skill: fix the README mention, don't skip the check.** The validator fails if any
on-disk skill is not named in `README.md`, so a brand-new skill trips check 4 until it is. That is
not a reason to skip: add the `README.md` line in the **same change**, re-run the validator until it
is green, and only then commit. The skill change and its README line are one commit (Step 2).

**Leak-scan exit codes — read the output, not just the status:**

| rc | Meaning | Action |
|----|---------|--------|
| 0 | Clean | Proceed — but read the output first (see next row). |
| 0 with `gitleaks not found — secrets pass SKIPPED` | Identity/path/health passed, but the scan's own secrets pass did not run (gitleaks absent) | Surface it — the tree is **not** fully clean until the secrets pass runs. Install `gitleaks` and re-run. |
| 1 | Hits found | Report the hits, stop. |
| 2 | Setup error (bad option, missing pattern file) | Stop — the gate is not doing its job. |

## Step 4 — Check the message, stage, commit

**Read the message before you commit it.** The leak gate is file-based and cannot see it, and the
history scan in Step 5 deliberately allowlists the public committer handle and the template names
inside `COMMIT_MSG` — so nothing catches those for you. Check the message yourself: no personal
name, no handle beyond the public committer one, no host, no health value, no personal data of any
kind. `CONTRIBUTING.md`: a name in a commit message is public forever.

Then:

```bash
git add <specific files for this commit>
git diff --cached --check            # final whitespace check over exactly the staged set
git commit -m "<type>: <message>"
```

Stage explicit paths only — never `git add -A` or `git add .`.

## Step 5 — Verify after commit (partial message backstop)

The history scan re-checks the tree content plus commit-message text for every pattern **except**
the ones it allowlists in a message (the public committer handle, and the template names). It is a
backstop, not the message gate — Step 4 is.

```bash
git log -p -1 | ./scripts/leak-scan.sh --no-gitleaks -
```

If it is red, fix the message before doing anything else — while the commit is unpushed:

```bash
git commit --amend -m "<corrected message>"
```

Then `git log --oneline -n <N>` to confirm. The whole-branch form of this scan is what `@create-pr`
runs before pushing.

## Privacy (non-negotiable)

Everything committed is treated as public, because the intent is to publish and history is forever.
Never commit personal health data — not in a skill body, a fixture, a commit message, or a branch
name. Keep placeholders (`<USER>`, `<YOUR_WEIGHT_KG>`, `<YOUR_HEALTH_DIR>`) and drop the values. The
gates enforce the mechanical part; the judgement is yours.

## Cross-thread isolation

More than one agent can work in this repo at once. Only stage files this session modified. If
`git status` shows a modified or untracked file you have no memory of touching, leave it alone and
say so — including untracked files that were already present before the session started.

## When to use

- The user says commit, stage, or wrap up.
- As the commit step of `@work`, before `@create-pr`.
- After a verified change, before opening a PR.
