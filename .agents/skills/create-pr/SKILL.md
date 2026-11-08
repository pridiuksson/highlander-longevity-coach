---
name: create-pr
description: "Lift commits onto a named branch and open a PR — without checkout. Runs diff check before pushing and flags skill changes for peer review. Safe when another agent works on the same branch. Designed as the step after @commit."
allowed-tools:
  - Bash
  - Read
  - Glob
argument-hint: "[branch-name]"
---

# Create PR

Takes commits that landed on the current branch (often `main`) and opens a pull request — **without ever running `git checkout`**. Runs a diff-quality check before pushing so the branch is clean when it lands on origin.

The full local-to-PR flow:

```
@commit        → commits land on current branch
@create-pr     → diff check → branch (no checkout) → push → PR
```

## Diff Check

Before pushing, run a lightweight quality gate:

```bash
git diff --check origin/main..HEAD
```

This catches whitespace errors, conflict markers, and blank-at-end-of-file issues. There is no build step — the repo contains only markdown documents and shell scripts.

**Advisory — peer review for skill changes**: if any changed file is under `.claude/skills/`, note it in the PR body. Skill definitions are self-contained and high-leverage — a second opinion is recommended before merge.

---

## Core Invariant

**Never run `git checkout`, `git switch`, or `git checkout -b`.**

Branch creation (`git branch <name> <sha>`) writes a ref without moving `HEAD`. Editors and parallel agents watch `HEAD` — since it never moves, they see nothing. This skill creates and pushes branches exclusively via ref writes and `git push`.

---

## Step 1: Identify Commits to PR

```bash
git fetch origin main
git log origin/main..HEAD --oneline
git rev-parse HEAD
```

Fetch first — ensures `origin/main` is current before diff checks. Without this, a recently-merged PR on main will inflate the diff scope.

- If `git log` is empty → "Nothing ahead of origin/main — nothing to PR" and stop.
- Capture `HEAD_SHA` for branch creation.

---

## Step 2: Run Diff Check

```bash
git diff --check origin/main..HEAD
```

**On failure**: whitespace errors, conflict markers, or trailing blank lines found. Fix the flagged lines. Do not create the branch or PR until clean.

**Check for skill changes** (advisory): if any file under `.claude/skills/` changed, set `SKILLS_CHANGED = true` for use in the PR body.

---

## Step 3: Determine Branch Name

If `$ARGUMENTS` contains a branch name → use it as-is.

Otherwise derive from the **first commit message** in the range (oldest first):

```bash
git log origin/main..HEAD --oneline --reverse | head -1
```

Derivation rules:
1. Strip conventional commit prefix: `type: ` → drop `type: `
2. Lowercase, replace spaces/slashes/parens with `-`
3. Remove special chars except `-` and `_`
4. Truncate to 50 chars
5. Prefix with type slug: `fix/`, `feat/`, `docs/`, `chore/`, `refactor/`

Examples:
- `docs: sync capacity model to Knowledge` → `docs/sync-capacity-model-to-knowledge`
- `chore: update grill skill prompt` → `chore/update-grill-skill-prompt`
- `feat: add Multica instance scanner` → `feat/add-multica-instance-scanner`

Check for collision on origin:
```bash
git ls-remote --exit-code origin <branch-name>
```
If exists, append `-2`, `-3` until free.

---

## Step 4: Create Branch and Push (no checkout)

```bash
git branch <branch-name> <HEAD_SHA>
git push -u origin <branch-name>
```

**Never run `git checkout`** — HEAD stays where it is.

If `git branch` fails (local branch already exists): `git branch -f <branch-name> <HEAD_SHA>`.

---

## Step 5: Draft PR Title and Body

**Title**: first commit message if single commit; synthesize from the range otherwise. Max 70 chars.

### Check: Advisory flags

Run: `git diff origin/main..HEAD --name-only` and flag:

- **Skill changes**: any file under `.claude/skills/` → `SKILLS_CHANGED = true`
- **Knowledge changes**: any file under `Knowledge/` → `KNOWLEDGE_CHANGED = true`

These flags go into the PR body's Review context section.

### Body template

**Copy this template exactly. Fill in the placeholders. Do not omit sections.**

```markdown
## Summary

<2–4 bullet points covering what changed and why>

## Changed Files

<details><summary>Files changed in this PR</summary>

<For each file from `git diff origin/main..HEAD --name-only`, add one line with the key change. Example:>

- `Knowledge/capacity-model.md` — document Oracle Cloud capacity snatch thresholds
- `.claude/skills/grill/SKILL.md` — tighten adversarial prompt for infra cost claims
- `scripts/snatch-capacity.sh` — add retry logic for Multica API rate limits

</details>

## Quality gate

- **Diff check**: ✅ `git diff --check` passed (no whitespace errors or conflict markers)
- **Peer review**: ⏭ not flagged / ⚠️ skill files changed — peer review recommended
- **Review**: ⏭ local review (run manually if needed)

## Test plan
- [x] Local: diff check passed
- [ ] CI: review (if applicable)

## Review context

> This section is written for the reviewer. It maps
> the flat diff back to intent so the reviewer can distinguish intentional
> changes from mistakes.

**Intentional changes that may look suspicious:**
<list any diff hunks that invert a condition, rename a value, flip an assertion,
or change a constant — with one-line rationale for each>

**Confirmed by testing:**
<what was verified before this PR — e.g. "diff check passed, skill logic reviewed locally">

**Not touched (do not flag as missing):**
<areas deliberately left unchanged — e.g. "grill skill core prompt unchanged,
only output format updated">
```

Write the Review context section honestly — if there are no suspicious-looking changes, say so. The goal is to pre-answer the reviewer's likely questions, not to fill space.

---

## Step 5.5: Verify Body Completeness

Before opening the PR, confirm ALL required sections are present in the body. Check each one:

- [ ] `## Summary` — 2–4 bullet points
- [ ] `## Changed Files` — collapsible list with per-file one-liners
- [ ] `## Quality gate` — with Diff check, Peer review, and Review sub-items
- [ ] `## Test plan` — local + CI checklist
- [ ] `## Review context` — Intentional changes, Confirmed by testing, Not touched

If any section is missing, add it before proceeding to Step 6.

---

## Step 6: Open PR

```bash
gh pr create \
  --title "<title>" \
  --body "<body>" \
  --base main \
  --head <branch-name>
```

---

## Step 7: Report

```
## PR Created

**Branch**: `<branch-name>` (created at <short-sha>, HEAD stayed on `<current-branch>`)
**PR**: <url>
**Commits**: <N>
**Checks**: ✅ diff check passed / ⚠️ skill changes flagged for peer review

| # | Commit |
|---|--------|
| 1 | <sha> <message> |

**Local state**: HEAD still on `<current-branch>` — no checkout performed.
```

---

## Already on a Feature Branch

If `git branch --show-current` returns something other than `main`:

- Skip branch creation entirely
- Run `git push -u origin <current-branch>` (or `git push` if tracking exists)
- Continue from Step 2 (run diff check, then proceed to draft + open PR)

The "no checkout" invariant is trivially satisfied — you're already on the right branch.

---

## Error Handling

| Condition | Action |
|-----------|--------|
| Nothing ahead of `origin/main` | Report and stop — nothing to PR |
| Diff check fails (whitespace/conflict markers) | Stop — fix flagged lines, do not create branch or PR |
| Branch name collision on origin | Append `-2`, `-3` until free |
| `git push` fails (non-fast-forward) | Report error — do not force push |
| `gh pr create` fails | Report error; branch already pushed, user can open PR manually |
