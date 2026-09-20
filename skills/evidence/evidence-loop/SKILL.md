---
name: evidence-loop
description: "Use when raw-data analysis yields standing, vouched claims."
version: 1.1.0
author: hermes (highlander-longevity-coach)
license: MIT
metadata:
  hermes:
    config:
      - key: health.health_dir
        description: "Root of your health data: device exports, SQLite DB, verified-data docs"
        default: "~/health"
        prompt: "Root of your health data: device exports, SQLite DB, verified-data docs"
    tags: [verification, data-analysis, peer-review, evidence]
    related_skills: [peer-review, deliberate, loop]
---

# Evidence Loop — from raw data to shipped, vouched claim

> **Config.** This skill reads its paths from `config.yaml`; the resolved values
> arrive in the `[Skill config]` block injected when this skill loads. In the
> commands below `$HEALTH_DIR` = `health.health_dir`.
> The `$VARS` above are shorthands for the keys, not environment variables — Hermes injects the
> values into the message, so substitute the resolved path. Never hardcode one: a clone can
> live anywhere, and `~/health` is only a default.

## When to Use

- Any analysis that will produce a **standing claim** in a runbook, doc, or coaching advice (health data, sensor data, any metrics).
- When data might **override human memory** or a previously published finding.
- After any incident where a probe/derivation was found wrong — before re-deriving, load this and follow the loop.

## When NOT to Use (gate, mirroring software-development/loop's 4-condition test)

Skip the full loop when ANY of these hold — just run the query and move on:
1. **The result is exploratory** — no sentence in any doc will cite it as a standing claim.
2. **Nothing is at stake against memory or prior findings** — the answer can't change advice or a record.
3. **No plausible confound exists** — pure counting (row totals, file sizes) with no era/pre-post structure.
4. **You cannot state what would change your mind** — if no control or sensitivity check could flip the conclusion, there is no loop, just an opinion.

Relationship to `software-development/loop`: that skill CONVERGES an artifact toward a testable spec (maker/checker cycles); this skill VALIDATES a claim's truth (replication/controls/vouch). They compose: when validating a claim requires building an artifact, use `loop` for the build and this for the evidence.

Validated across the 2026-08-30 session: 6 correction/analysis loops, all productive, zero silent errors shipped. Clean-context usability test passed same day (cold reader answered a disguised version of the nap incident correctly on all 4 probes: step ordering, replication-must-differ, testimony handling, gate application).

## The loop (in order, no steps skipped)

1. **Re-derive from raw.** Never trust a derived series — including your own earlier probes. Every standing number gets re-computed from the source DB/files in this session.
2. **Dual derivation must AGREE — and must be GENUINELY different.** Two runs of the same predicate with different formatting is ceremony, not replication (loop's anti-ritual rule applies to evidence too). Different predicates, different aggregation layer, different code path. Agreement = evidence. Disagreement = bug alarm — stop, diagnose WHICH assumption diverged, fix, re-run. (Caught `in_sleep_window` night-window misuse this way: n=220 vs n=109.)
3. **Testimony anchor-check.** Ask the human "does this match lived experience?" One sentence of testimony falsified a 4-expert deliberation's x-axis. Divergence is a finding: record it with BOTH sides, don't paper over, don't auto-pick a winner. Memory may track intent, data tracks incidence — both belong in the record.
4. **Classify before interpreting.** Taxonomy first, statistics second. (392 "naps" were evening dozes/night-splits/post-wake — mislabeled classes poisoned every sentence built on the label.)
5. **Controls before headlines.** For any pre/post or era contrast ask: "what else changed at the same time?" Season-matching killed an apparent "assist effect" to a NULL. Naive baselines are the #1 artifact source.
6. **NULLs are results.** Ship them with the same rigor as positives. A control that kills your expected effect is the product working.
7. **Peer-review vouch** before data overrides human memory or a prior finding. Fact-check verifiable claims yourself first; hand the peer only genuine judgment calls; verify the auditor's claims before merging its corrections (auditors fabricate too).
8. **Ship immediately:** evidence script + doc updates + conventional commit into the EXISTING PR branch. Every claim in a doc must have its committed script one search_files away.

## Tooling discipline

- Recurring time/stat operations → canonical tested module (e.g. `health.health_dir/health_time.py`, 22 regression tests, one test per real incident). Ad-hoc probes are for exploration only — never cite a probe's number as a standing claim.
- New module → tests FIRST for each known failure class (one per past incident: utc-as-local, naive circular median, fragment poisoning, DST fold).
- Predicate gotchas bite twice: window functions have siblings with different semantics (`in_sleep_window` = night [18,06), NOT "evening"); never double-convert an already-local timestamp.

## Pitfalls (all hit in production)

- **Claiming edits you didn't ship.** Edit a live file outside the repo → commit message says "skill updated" → repo never got it. Verify with `git show --stat` + `diff` before claiming. Live skills tree may be standalone, not vendored.
- **Wrong-denominator rates.** First-to-last-event span ≠ fixed era window. Report both when they differ.
- **Broken arithmetic in prose.** "28 sessions ≈ every 3rd night" — no: 28/34 weeks ≈ 0.8/wk. Rates come from code, not narration.
- **Memory drift.** Environment facts (symlinks, paths, tree layouts) rot. Diff-check before trusting; the drift-sweep before session close is mandatory.

## Ship ledger

Each validated loop appends one line to the runbook's corrections/changelog section (e.g. run-008's CORRECTIONS LEDGER): `<date> — <claim> — <what changed> — <evidence script>`. Compounding lessons go into the skill's Pitfalls, not prose. This mirrors loop's `.loop-state.json` lessons array: knowledge compounds across runs, not just within them.

## Trust contract (user-accepted 2026-08-30)

Data overrides human memory ONLY when: (a) extraction tooling is tested/canonical, (b) dual derivation agrees, (c) peer-review concurs. Human testimony always serves as anchor-check and stays in the record when it diverges.
