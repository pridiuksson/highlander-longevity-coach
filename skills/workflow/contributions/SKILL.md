---
name: contributions
description: "Contribute locally-proven skill improvements back to the upstream kit repo — capture early, submit deliberately. Use when a local skill edit might be worth upstreaming, or when triaging the contributions ledger."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [git, gh]
metadata:
  hermes:
    tags: [contributing, upstream, ledger, workflow, skills]
---

# Contributions — capture early, submit deliberately

Skills adopted from the upstream kit get improved locally through real use. Most improvements are
instance-specific; a few are generalizable and belong upstream. This skill closes that loop without
a nag cron: capture the *reason* at edit time (cheap, lossy), decide at a deliberate monthly
moment (costly, informed).

Two axioms the mechanism rests on:

1. **The change is always reconstructible; the reason never is.** `git diff <base>` regenerates
   every change. Why it was made exists only in the ledger. Capture therefore optimizes for reason,
   not for diff — a mechanical row without a why is noise, not a capture.
2. **Capture and submit fail in opposite directions.** A missed capture costs nothing (safe). A
   lost or rushed *decision* ships unvalidated patterns upstream (unsafe). So capture is a
   reflex; submission is gated on validation and a calendar, never on "next time I happen to sync".

## The ledger

One file: `<state-dir>/CONTRIBUTIONS.md`, two sections. The state dir is wherever the adopter's
skill-sync bookkeeping lives (instance-side, never inside the repo clone).

### Section 1 — Candidates and decisions (append-only)

One row per contribution decision. Append at **capture time** only the reason; everything else is
filled at the **submit check**:

```markdown
### <skill-name> — <capture date>
- Why: <one line — the improvement, in the words that made it feel worth upstreaming>
- Status: candidate
```

States, in order:

| State | Meaning |
|---|---|
| `candidate` | Captured, not yet judged |
| `open` | PR filed — record PR URL and the **submitted hash** (see below) |
| `merged` | PR merged — record the upstream merge SHA; **re-verify by hash each sync** |
| `closed` | PR closed unmerged — record the reason; the row is history, do not resubmit silently |
| `never` | Judged instance-specific — append to Section 2 instead, or annotate here with the reason |

Rules:

- **Status is derived where possible, stored where it cannot be.** At the submit check, recompute
  the local skill's normalized hash against the row's recorded hashes: equal to `merged`'s hash →
  quiet; different → the delta evolved again, reopen as `candidate` (append a new `Why` line — do
  not edit the old one).
- **The submitted hash is a normalized content hash, not a commit SHA.** Hash the skill directory
  per file (including `references/` and `scripts/` — SKILL.md-only hashes miss reference drift),
  after normalizing placeholders (`<YOUR_*>` fields, `${HERMES_SKILL_DIR}`) so renames and re-homing
  do not read as changes. Record the upstream `base_sha` the hash was taken against.
- **Key rows by skill name, not local path.** Renames must not orphan a row.

### Section 2 — Instance-specific (seeded once, reviewed by date)

Skills deliberately kept local, with a reason and a review-by date. Not a graveyard: an entry whose
review-by date has passed is re-asked, and the default answer when a delta turns out to be
generalizable is **"extract the abstraction and contribute that"**, not silence.

## The capture reflex

When a session improves an adopted skill for a live reason, append the reason line **before the
turn ends**:

```markdown
### <skill> — <YYYY-MM-DD>
- Why: <one line>
- Status: candidate
```

That is the whole capture. Do not diff, do not hash, do not open a PR. A capture with no reason is
deleted at the next check; the diff regenerates the what, only the session knows the why.

## The monthly submit check (calendar-driven, not drift-driven)

A pending candidate is a **decision, not drift** — it generates no content change of its own, so
"check next sync" never fires for quiet skills. The check is a dated calendar item (monthly; a
missed month is fine, an unbounded "next sync" is not).

Procedure, per `candidate` row:

1. **Validate.** The delta must have survived real use — at least one live session where the
   improved behavior actually ran and held. A zero-session delta is premature; leave it as
   `candidate`.
2. **Judge.** Could another adopter of the upstream kit use this? Instance-specific (local paths,
   profile names, personal workflow) → Section 2 with a reason. Generalizable → submit.
3. **Submit.** Re-home the delta into a clone of the upstream repo (`skills/<stage>/<name>/`),
   satisfy the repo's conventions (self-contained, `license:`, README mention if a new skill),
   then ship with the repo's own `@commit` and `@create-pr` skills — never a hand-rolled
   `gh pr create` (the gates and body template are the point). Record `open` + URL + submitted
   hash + base_sha.
4. **Generalize-then-contribute.** For Section 2 entries whose delta is generalizable but its
   values are not: upstream the abstraction with placeholder values, keep the concrete values local.

## Anti-patterns

| Don't | Do |
|---|---|
| File the PR at edit time | Capture the reason; submit at the dated check after validation |
| Track dispositions as flags in the sync manifest | The ledger owns decisions; the manifest owns drift |
| Add a "contribute back" note inside each skill's SKILL.md | It pollutes every future sync diff |
| Submit on "next sync" | Syncs fire on drift; decisions need a calendar |
| Hand-roll `gh pr create` | Use the upstream repo's own workflow skills |
| Treat `merged` as permanent | Hash-check on every sync; re-open what evolved |

## When to use

- A session improves an adopted upstream skill → capture reflex.
- The monthly check arrives → triage `candidate` rows through validate → judge → submit.
- A sync finds a skill diverged → consult the ledger first: `merged` rows are upstream's now,
  `never` rows are owned forks, unknown drift is a new candidate.
