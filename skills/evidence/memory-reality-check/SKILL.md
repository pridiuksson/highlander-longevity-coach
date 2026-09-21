---
name: memory-reality-check
description: "Diff behavioral claims in MEMORY/USER against data sources; fail-closed."
version: 1.1.0
author: Hermes Agent (ported from a design proven in private use, 2026-09)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    config:
      - key: health.reality_sources_dir
        description: "Directory of reality-source scripts (each prints a JSON signatures dict)"
        default: "~/health/reality-sources"
        prompt: "Directory of reality-source scripts (each prints a JSON signatures dict)"
      - key: health.reality_max_stale_days
        description: "Max data age (days) before the check refuses to verify (STALE)"
        default: "10"
        prompt: "Max data age (days) before the check refuses to verify (STALE)"
    tags: [verification, memory, drift, health, quantified-self]
    related_skills: [evidence-loop, proactive-coach, peer-review]
---

# Memory Reality Check

A memory entry can be textually perfect and factually wrong: "training 3-4x/wk" survives
every audit while the body changed. This skill closes that gap — it enumerates behavioral
claim sites in `MEMORY.md` / `USER.md`, diffs each against reality signatures from
pluggable data sources, and reports drift. **It never auto-edits memory**: the person's
own testimony is the arbiter of what "deliberate change" means.

## When to Use

- Part of a weekly sweep or any audit of standing behavioral claims in memory.
- After a health/workflow data import: verify memory claims still match the fresh data.
- When a stored claim and a measurement disagree and you need a structured diff, not vibes.

## When NOT to Use

- The claim is about the environment (paths, tool versions) — audit those directly.
- No reality source exists for the claim's metric — the check reports UNVERIFIED and a
  congruent verdict is then forbidden; do not run it to generate a clean bill.

## Prerequisites

- `python3` (stdlib only — no dependencies).
- At least one **reality source** (see below). Without one the engine exits 2 (NO_DATA).

## How to Run

```bash
python3 ${HERMES_SKILL_DIR}/scripts/reality_check.py \
  --memory-dir ~/.hermes/memories \
  --sources-dir "$HEALTH_REALITY_SOURCES_DIR" \
  --max-stale "${HEALTH_REALITY_MAX_STALE_DAYS:-10}"
bash ${HERMES_SKILL_DIR}/scripts/regression_suite.sh   # before changing anything
python3 ${HERMES_SKILL_DIR}/scripts/reality_check.py --demo   # end-to-end on obviously-fake data
```

In an agent session, `$HEALTH_REALITY_SOURCES_DIR` is the resolved value of
`health.reality_sources_dir` and `$HEALTH_REALITY_MAX_STALE_DAYS` of
`health.reality_max_stale_days` from the `[Skill config]` block.

## Quick Reference — exit contract

| Exit | Meaning | Consumer action |
|---|---|---|
| 0 | PENDING-REVIEW: sites enumerated, awaiting review. **NOT a clean bill.** | Reviewer (agent/human) reviews every site; see Procedure |
| 1 | DRIFT detected (unparseable lines, if any, are printed too) | Confirm with the user; classify as a DIGEST candidate |
| 2 | NO_DATA / NO_CLAIMS (unparseable `data_end` becomes a source error → 2) | Fix the source or the memory path; do not treat as clean |
| 3 | UNPARSEABLE behavioral lines | Fix the wording or extend the grammar; fail-closed |
| 4 | STALE data, a FUTURE `data_end` (bad source clock), or unprovable freshness | Refresh the source; never audit stale data confidently |

The pending report is self-contained: it prints the winning source, its `data_end` and
`coverage_days`, and every actual value — the reviewer does not need to re-run sources.
`--quiet` drops only the per-line ledger detail; the PENDING-REVIEW banner and exit code
are unchanged (a cron grepping for the marker must still find it on exit 0).

**The machine never says CONGRUENT.** The engine's output is an input to review, not a
verdict. Two hard rules for the reviewer:

1. Every `NO-SITE` line in the SCAN-LEDGER must be accounted for before any clean bill —
   a behavioral line the grammar cannot see is the engine's known blind spot, made
   visible, not solved. **Scope of the blind spot:** lines reaching the ledger have a
   number near an activity noun. Pure prose ("I've been running less lately" — no digit)
   never enters the scan; the reviewer reads the memory files with their own eyes for
   that class. The ledger makes the machine-visible portion auditable; it cannot make
   prose visible.
2. Any UNVERIFIED site forbids a clean bill. A missing metric is a source limitation,
   not silence.

## Procedure

1. **Run the engine** (command above). Read the full report; do not branch on the exit
   code alone.
2. **Review the SCAN-LEDGER.** Account for every line: sites to diff, NO-SITE lines to
   read with your own eyes.
3. **Diff each site against the quoted actual value.** The report cites the source line
   and the measured value; check the source's `data_end` and `coverage_days` before
   trusting a rate.
4. **Verdict, per the evidence-loop trust contract:**
   - Drift confirmed → ask the person. Testimony decides deliberate-change-vs-drift.
     Update memory only after their answer. Never auto-edit identity memory.
   - Everything accounted for, nothing unverified, user confirms unchanged → record the
     congruent verdict **in your session notes**, not by editing the engine's output.
5. **Route drift findings through the proactive-coach gate** as DIGEST candidates: the
   five-test insight gate applies (a drift the user already knows about is correctly
   rejected). Ledger the delivery or the reject.
6. **Never feed this output as satisfying evidence-loop's dual-derivation contract** —
   a single tolerance diff is a heuristic, not a verification.

## Reality sources (the contract)

Each `*.py` in `health.reality_sources_dir` prints one JSON dict to stdout:

```json
{"runs_per_week": 2.0, "sleep_avg_h": 7.0, "active_days_per_week": 5.0,
 "data_end": "2026-09-19T17:45:01+00:00", "coverage_days": 28}
```

- `data_end` — ISO 8601 timestamp of the newest data point. Drives freshness and ranking
  (freshest wins; ties break by source filename — deterministic, but name your sources
  with intent: the alphabet is the tie-breaker). A `data_end` in the FUTURE is refused
  (exit 4) — a bad source clock must not read as fresh.
- `coverage_days` — the window the source actually covers. Rates MUST be computed over
  this window, not a nominal one (a short-history store otherwise deflates every rate
  into false congruence).
- Every metric value must be a NUMBER — a non-numeric value marks the whole source a
  SOURCE ERROR (exit 2, listed), never a crash that reads as drift.
- Any `*_avg_h` key is read as a duration metric; `active_days_per_week` backs the
  "most days" / "N days a week" claims; `<noun>_per_week` backs cadence claims. When
  several `*_avg_h` metrics exist, the claim's own words pick the key ("sleep 7.5h" →
  `sleep_avg_h`, word-boundary match); zero or several word-matches → UNVERIFIED, never
  a guessed drift. Residual: a LONE `*_avg_h` metric whose stem appears as a word in the
  line is trusted even if it is the wrong metric ("Sleep 9h, RHR 50." with only
  `rhr_avg_h` present) — pin the residual: name your metrics so their stems appear
  verbatim in the claim, or accept the UNVERIFIED route.
- Conflicts are scoped per activity: "Runs 2/wk" + "Gym 4x/week" are two claims, never
  a conflict; "Runs 2/wk" + "Run 5 per week" is one.
- The engine validates freshness but **cannot validate honest coverage** — a lying
  `coverage_days` silently moves every rate. That is a documented limitation: pick
  sources you trust, and cross-check a surprising rate manually before acting.
- **Point-claim tolerance is max(0.5, 0.25*claim) per week** — tight at small claims
  (runs 2/wk vs 2.6/wk is drift). Deliberate: per-week cadences under 1.0/wk are noise
  territory; a real change usually clears 25%. Borderline ranges get NOTE[...-BORDER]
  instead of exit 1; borderline points do not — say so if your memory uses fine-grained
  point claims.
- **Duration claims are noun-first only**: "sleep 7.5h" parses; "7.5 hours of sleep"
  does not — it never reaches the scan (documented blind spot of guard #1's scope).
  Keep sleep claims noun-first in memory, or extend the grammar with a suite case.
- **Sources run as arbitrary code** with no sandbox: pointing `health.reality_sources_dir`
  at an untrusted path is code execution. Keep it user-owned.

Multiple sources: the freshest `data_end` wins (ties break by source filename). A failing
source is reported (SOURCE
ERRORS section), never fatal — a broken source must not read as drift.

## Pitfalls

- **Regex cadence gaps are structural, not bugs.** The grammar covers six generic shapes;
  anything else fails closed as UNPARSEABLE. Do not "fix" wording to dodge the verdict —
  extend the grammar consciously, with a suite case.
- **Prescriptive lines (protocol/targets) are suppressed, not audited.** They describe
  intent, not behavior. If a suppressed line carries a real frequency, reword it so it
  gets audited — or accept it stays unaudited, deliberately.
- **Point claims inside a range line are deduped** (a range is the more specific
  reading). A cap (≤N) is one-sided: under-cap is never drift.
- **Borderline values** (just outside a claimed range, inside the grace band) print
  NOTE[...-BORDER]: these are judgment calls for the reviewer, deliberately not exits.
- **Never run the suite against live memory.** It seeds copies in a temp dir by design;
  keep it that way.

## Verification

- `bash ${HERMES_SKILL_DIR}/scripts/regression_suite.sh` — all cases green before and
  after any change. Cases assert deterministic enumerator behavior on synthetic
  fixtures; a live verdict belongs to the reviewer, never the suite.
- `python3 ${HERMES_SKILL_DIR}/scripts/reality_check.py --demo` — end-to-end on an
  obviously-fake temp fixture; expect exit 0 with PENDING-REVIEW and ONE UNVERIFIED
  site (the `Runs ≤2/wk` cap — the demo source covers sessions/active-days/sleep).
- After changing the grammar: add a case that FAILS against the old behavior, or the
  fix is not pinned.
