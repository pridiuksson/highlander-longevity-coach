---
name: commit
description: "Structured commits following conventional commit conventions. Local mode: autonomous 3-step flow (gather → quick checks → plan & execute). CI mode: autonomous — no prompts, commits with 🤖 prefix, structured output for PR comments."
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
argument-hint: "[ci]"
---

# Structured Commits

Create well-scoped, readable commits from the current changes. Groups files by independent intent, applies conventional commit conventions.

**Dual mode**: local (autonomous, 3-step) and CI (autonomous, no prompts). CI mode activates when `$ARGUMENTS` contains `ci` **or** env `CI=true`.

---

## Commit Format

Conventional commits with mandatory type:

```
<type>: <imperative description>
```

**Types:**

| Type | Meaning |
|------|---------|
| `feat` | New feature or behavior |
| `fix` | Bug fix |
| `refactor` | Behavior-preserving restructure |
| `test` | Test files only |
| `docs` | Knowledge/*.md, README |
| `chore` | Config, deps, CI |
| `style` | Formatting only, no logic change |

**Skills**: use `refactor` for behavior-preserving rewrites, `feat` for new capability, `fix` for bug fixes. Don't default to `chore`.

**Prefix by mode:**

| Mode | Prefix | Example |
|------|--------|---------|
| Local | (none) | `fix: update snatcher cron schedule to 6-hour intervals` |
| CI | `🤖` | `🤖 fix: handle missing reference in ticket body` |

---

## Commit Message Rules

1. **Imperative mood**: "add rollback section to ticket template" not "added rollback section"
2. **Why, not what**: "fix snatcher log path (was pointing to /tmp)" not "change snatcher log path"
3. **No attribution**: Never add co-author, "Generated with Claude", or "Co-Authored-By" lines
4. **Subject under 72 chars**, body wrapped at 72 chars. Body is required for non-trivial changes — it captures rationale that git blame readers will need.

---

## Commit Splitting Rules

Split by **independent intent**, not rigidly by file type. Coupled changes stay together:

| Scenario | Split? | Rationale |
|----------|--------|-----------|
| New skill + its Knowledge doc update | **No** | Doc describes what the skill does |
| New skill + unrelated fix to another skill | **Yes** | Independent intents, independent revert risk |
| Skill implementation change + its SKILL.md | **No** | Doc describes what the code does
| Config change + its Knowledge doc update | **No** | Doc reflects the config
| Knowledge doc rewrite + skill adaptation | **Depends** | If the doc rewrite enables the skill change, keep together; otherwise split |
| Multiple skill adaptations following same pattern | **Per-skill** | Each skill is independently revertable |
| Only `Knowledge/*.md` changes | **By intent** | If updating multiple docs for different reasons, split; if rewriting all docs for one purpose, keep together |

**Coupling rule**: If two changes must be reverted together, they must be committed together.

---

## Changed Files Context

!`git status --short 2>/dev/null`
!`git diff HEAD 2>/dev/null; git diff --cached 2>/dev/null`

---

# Local Mode (default)

Autonomous 3-step flow. Plans and executes without confirmation.

## Step 1: Gather Changes

1. **Review conversation context** — what was done in this session (primary source for intent and why)
2. **Read git output above** — what's actually on disk (source of truth for what gets committed)
3. **Reconcile** — if conversation mentions changes that `git status` doesn't show, files may be unsaved. Ask user to save before proceeding.

If no changes found → report "Nothing to commit" and stop.

## Step 2: Quick Checks

Fast quality gate before committing.

### Blocking: Whitespace & Conflict Markers

```bash
git diff --check
```

**On failure**: report the errors, **stop**. Fix whitespace issues or resolve conflict markers before committing.

### Blocking: Pre-staged Files

```bash
git diff --cached --name-only
```

If this returns any files **not modified in this session's conversation context**, another agent or session pre-staged them. List the unexpected files and **stop** with:
> "⚠️ These files are pre-staged by another process: `<file list>`. Run `git reset HEAD <files>` to unstage them, or `git commit` manually before re-running /commit."

This prevents accidentally committing another session's work. Files you modified this session that happen to be pre-staged are fine — only flag files you have no memory of touching.

### Blocking: Python Syntax Validation

```bash
{ git diff --name-only HEAD -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u | xargs -r python3 -m py_compile
```

**On failure**: report the failing file and line, **stop**. Fix the syntax error before committing.

### Advisory Flags (non-blocking)

After checks pass, compute advisory notes from the changed files. Display after the commit plan in Step 3. These **never block** a commit.

**Suggested verification** — match top-to-bottom, first match wins:

| If changed files include... | Suggest |
|---|---|
| `.claude/skills/*/SKILL.md` | Peer-review the skill changes before pushing |
| `Knowledge/oracle.md` (SSH hosts, connection strings, IPs) | Verify SSH/login commands still work |
| `Knowledge/multica.md` (project ID, connection details) | Verify project ID matches `multica project list` output |
| Only `Knowledge/*.md` (no infra details changed) | No verification needed |

**Uncommitted changes** — after planning commits in Step 3, cross-reference the planned files against `git status --short`. If there are changed files not included in any planned commit, warn: "⚠️ Uncommitted changes not in this commit plan: `<file list>`. Stage before proceeding, or commit separately."

**Cross-thread isolation** — multiple agents may work in the same repo simultaneously. Only stage files that appear in this conversation's context as having been modified by this session. If `git status` shows modified (`M`) or untracked (`??`) files you did not touch in this conversation, leave them completely unstaged. Never commit another agent's work, even if it looks related. If a file appears in `git status` but you have no memory of modifying it this session, skip it and warn: "⚠️ `<file>` is modified but was not touched in this session — leaving it unstaged."

## Step 3: Plan & Execute

Group files by independent intent using the splitting rules. Plan the commits, then execute immediately without confirmation.

For each group, determine:

- **Type** from the conventional commit types table
- **Message** following the commit message rules
- **Files** to stage for this commit

Present the plan:

```
### Commit Plan (N commits)

**1.** `type: message`
   - `path/to/file1`
   - `path/to/file2`

**2.** `type: message`
   - `path/to/file3`
```

### Execute

1. For each planned commit: `git add` specific files per commit (never `-A` or `.`), then `git commit -m "<message>"`
2. Show `git log --oneline -n N` to confirm
3. Show advisory flags from Step 2 — if any apply

---

# CI Mode

Activated when `$ARGUMENTS` contains `ci` **or** env `CI=true`. Autonomous — no interactive prompts, no confirmation.

## CI Git Context

The workflow runs `git reset --soft origin/main` — all changes are staged. **`git diff --cached` is the canonical diff source.** `git diff HEAD` (without `--cached`) shows nothing.

## CI Step 1: Gather Changes

1. **Read `git diff --cached`** — the only source of truth in CI (no conversation context)
2. **Infer intent from paths and diff content**:
   - `Knowledge/*.md` changed + skill files → doc sync with skill changes (type: `fix` or `docs`)
   - Only `Knowledge/*.md` changed → doc sync (type: `docs`)
   - Only `.claude/skills/` changed → skill adaptation (type: `chore`)
   - Mixed files → analyze hunks to determine if coupled or independent
3. If no staged changes → report "Nothing to commit" and stop
4. **Validate Python** — run `git diff --cached --name-only -- '*.py' | xargs -r python3 -m py_compile`. If any staged `.py` file fails to parse, report the error and stop (see Bail-out Conditions).

## CI Step 2: Plan Commits

Same splitting rules and message rules as local mode, with these additions:

- **🤖 prefix**: All CI commit messages start with `🤖`
- **Batch when ambiguous**: If splitting intent is unclear from the diff alone, prefer a single well-described batch commit over incorrect splits. The coupling rule applies — when in doubt, commit together.

## CI Step 3: Execute

1. **No confirmation** — plan and execute immediately
2. For each planned commit:
   - `git reset HEAD` — unstage everything first to start clean
   - `git add <specific files>` — stage only this commit's files
   - `git commit -m "🤖 <type>: <message>"`
3. Never use `git add -A` or `git add .`

## Bail-out Conditions

| Condition | Action |
|-----------|--------|
| No staged changes | Report "Nothing to commit", exit cleanly |
| Python syntax error in staged `.py` file | Report `py_compile` error with file + line, **do not commit** |
| `git commit` fails | Report error with `git status` output, **do not retry** |
| Merge conflict | Report error, **do not attempt resolution** |

Maximum: **1 attempt** per commit. If it fails, report and stop.

## Structured Output

End with a summary suitable for PR comments:

```
## Commits Created

| # | Message | Files |
|---|---------|-------|
| 1 | 🤖 fix: ... | file1, file2 |
| 2 | 🤖 docs: ... | Knowledge/xxx.md |

**Total**: N commit(s), M file(s)
```

If nothing to commit:
```
## Commits Created

No changes to commit.
```

---

## Examples

**Local — coupled changes stay together:**
```
docs: rewrite multica.md to focus on General project
 - Knowledge/multica.md
 - Knowledge/oracle.md
```
Both docs were rewritten as part of the same project reorientation → one commit.

**Local — independent intents split:**
```
1. refactor: streamline peer-review skill to essentials
   - .claude/skills/peer-review/SKILL.md

2. refactor: adapt ticket skill for infra/ops project
   - .claude/skills/ticket/SKILL.md
```
Two independent skill rewrites → two commits.

**CI — fix with doc sync:**
```
1. 🤖 fix: correct project ID in multica.md
   - Knowledge/multica.md
```
