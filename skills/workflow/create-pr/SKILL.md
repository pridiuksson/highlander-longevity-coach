---
name: create-pr
description: "Ship the current commits as a pull request without ever moving HEAD — leak-gated. Use after @commit when the user asks to open a PR, push a branch, or 'get this reviewed'. Runs the full pre-push gate (tree + history + skills + secrets) before pushing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [git, gh]
metadata:
  hermes:
    tags: [contributing, git, pull-request, workflow, leak-gate]
---

# Create PR — leak-gated, no checkout

Take the commits that landed on the current branch and open a pull request. Two invariants:

1. **Never run `git checkout`, `git switch`, or `git checkout -b`.** Branch creation writes a ref
   without moving `HEAD`. Anything watching `HEAD` — an editor, another agent on the same checkout —
   sees nothing.
2. **Every available pre-push gate must pass.** A red gate means stop; do not push and "let CI catch
   it". A gate whose tool is missing is reported as unverified — never skipped silently.

```
@commit → @create-pr
```

## Step 1 — Identify what to PR

```bash
git fetch origin main
git log origin/main..HEAD --oneline
git rev-parse HEAD
```

Fetch first so `origin/main` is current. Empty log → "Nothing ahead of origin/main" and stop.
Keep the `HEAD` SHA for branch creation.

## Step 2 — Pre-push gates

Run in this order. Any failure stops the push. Gate 5 requires `gitleaks`; if it is missing, report
the secrets checks as unverified — not clean.

```bash
git diff --check origin/main..HEAD      # 1. whitespace / conflict markers

./scripts/leak-scan.sh .                # 2. leak gate, tree (+ its own gitleaks pass)

git log -p --all -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -   # 3. leak gate, full history

python3 scripts/validate-skills.py .    # 4. skill structure + README consistency

gitleaks detect --source . --log-opts="--all"   # 5. secrets over every commit (if installed)
```

Notes that matter:

- **Two passes, two scopes.** Gate 2 (`leak-scan.sh` in directory mode) has an identity/path/health
  pass that walks the **whole working tree** with `find` — so `.gitignore` exempts nothing, and a
  scratch file anywhere in the repo, even in gitignored `staging/`, is scanned. Move stray files
  outside the repo. Its embedded `gitleaks` pass is different: it inspects **committed content** and
  ignores uncommitted files.
- **The embedded `gitleaks` pass is not full-history.** Verified: a secret committed and later
  removed is missed by `gitleaks detect --source .` but caught with `--log-opts="--all"` — which is
  what gate 5 adds, so gate 5 is not redundant.
- **If `gitleaks` is not installed**, gate 2 prints `gitleaks not found — secrets pass SKIPPED` and
  can still exit 0 on a clean pattern pass — and gate 5 cannot run either. Install `gitleaks` so both
  secrets passes are available, and until then report the secrets checks as **unverified**, never as
  clean. CI does not fill the gap: its secrets pass has the same committed-content scope and will
  not catch a removed secret.
- **Gate 3 catches personal names in commit messages**, but it exempts the public committer handle
  and the template profile names. Check those yourself before committing — `@commit` Step 4 does.
- Leak-scan exit codes: `0` clean, `1` hits, `2` setup error. Anything but `0` stops the push.

**Advisory — skills changed.** If any file under `skills/**` changed, set `SKILLS_CHANGED = true`
and flag it in the PR body. Skill definitions are self-contained and high-leverage; a second opinion
(`@peer-review`) is recommended before merge. This repo's convention is a review pass before and
after building or changing a skill.

## Step 3 — Branch name

If the user gave a branch name, use it. Otherwise derive it from the **first** commit in the range:

```bash
git log origin/main..HEAD --oneline --reverse | head -1
```

Drop the `type: ` prefix, lowercase, replace spaces/slashes/`()` with `-`, keep `-` and `_`,
truncate to 50 chars, and prefix with the type slug (`fix/`, `feat/`, `docs/`, `chore/`,
`refactor/`). Example: `docs: sync onboarding` → `docs/sync-onboarding`.

Check the name is free on **origin and locally** — a local branch is invisible to `ls-remote`:

```bash
git ls-remote --exit-code origin <branch-name>    # origin
git show-ref --verify refs/heads/<branch-name>    # local
```

If either exists, append `-2`, `-3`, … until both are free.

## Step 4 — Create and push (no checkout)

```bash
git branch <branch-name> <HEAD_SHA>
git push -u origin <branch-name>
```

`git branch` only writes a ref; `HEAD` does not move. `git branch -f` is safe **only** when a local
branch of that name already exists *and* already points at `HEAD_SHA` — otherwise choose a fresh
name, because `-f` silently repoints it. Never force-push.

## Step 5 — PR title and body

Title: the single commit message if there is one, otherwise synthesised from the range; ≤ 70 chars.

Fill **every** section — a missing section is a defect, not a style choice:

```markdown
## Summary

<2–4 bullets: what changed and why>

## Changed Files

<details><summary>Files changed in this PR</summary>

- `path/to/file` — one line on the key change
- `path/to/other` — one line on the key change

</details>

## Quality gate

- **Diff check**: ✅ `git diff --check origin/main..HEAD` passed
- **Leak gate (tree)**: ✅ `./scripts/leak-scan.sh .` passed
- **Leak gate (history)**: ✅ full-history scan passed
- **Skill validation**: ✅ / ⏭ no skills changed
- **Secrets (full history)**: ✅ `gitleaks --log-opts="--all"` passed / ⏭ not installed — local-only; CI does not run this
- **Peer review**: ⏭ not flagged / ⚠️ skills changed — review recommended

## Test plan

- [x] Local: all pre-push gates passed
- [ ] CI: leak gate (runs on push/PR)

## Review context

> Written for the reviewer: maps the diff back to intent.

**Intentional changes that may look suspicious:**
<list any inverted condition, renamed value, changed constant — one line of rationale each>

**Confirmed by testing:**
<what was actually verified>

**Not touched (do not flag as missing):**
<areas deliberately left unchanged>
```

## Step 6 — Open the PR

```bash
gh pr create --title "<title>" --body "<body>" --base main --head <branch-name>
```

Once active, CI (`.github/workflows/leak-gate.yml`) re-runs the tree gate (including its own
`gitleaks` pass), the skill validator, and the history scan on every push and PR — server-side, so
the local `--no-verify` bypass does not apply. It runs the repo's own `scripts/`, so treat it as a
second opinion, not an independent auditor. It does **not** run a full-history `gitleaks` pass;
gate 5 is local-only.

## Step 7 — Report

```
## PR Created

**Branch**: `<branch-name>` (at <short-sha>; HEAD stayed on `<current-branch>`)
**PR**: <url>
**Commits**: <N>
**Checks**: ✅ gates passed / ⚠️ skills flagged for peer review

| # | Commit |
|---|--------|
| 1 | <sha> <message> |

**Local state**: HEAD still on `<current-branch>` — no checkout performed.
```

## Already on a feature branch

If `git branch --show-current` is not `main`: skip branch creation, push the current branch
(`git push -u origin <current-branch>`, or `git push` if it already tracks), and continue from
Step 2. The no-checkout invariant is satisfied trivially.

## Error handling

| Condition | Action |
|-----------|--------|
| Nothing ahead of `origin/main` | Report and stop. |
| Any pre-push gate fails | Stop. Fix the flagged lines; do not push. |
| Branch name exists on origin | Append `-2`, `-3`, … |
| `git push` fails (non-fast-forward) | Report the error. Do **not** force-push. |
| `gh pr create` fails | Report; the branch is already pushed, so the PR can be opened by hand. |

## When to use

- After `@commit`, when the change is ready for review.
- As the final step of `@work`.
