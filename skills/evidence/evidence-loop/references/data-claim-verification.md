---
name: data-claim-verification
description: "Verify a claimed stat before trusting or repeating it."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [audit, verification, sqlite, sql, data-analysis, re-derivation]
---

# Data-Claim Verification (audit a number before you trust it)

## When to Use

- Someone hands you a stat/headline to confirm, quote, or build on: "X rose 2.6×", "record
  low", "% of all", "biggest since 20XX".
- You are about to repeat an analytic number from a findings doc, a prior session, or a PR.
- You are auditing a data script's output (labels/tiers, ratios, seasonal windows).

Any analytic headline — a ratio, a "record low/high", a percentage, a YoY rise — inherits
false authority once written down. When asked to confirm OR repeat such a claim, don't
trust the summary: **re-derive it from the primary data yourself**, then diff your numbers
against the claim. This is the class-level version of the garmin/samsung conscious-tier
audit (see `references/conscious-tier-audit.md` for a worked example, and
`references/garmin-baseline-audit.md` for a full baseline-table re-derivation with
the three-way diff sequence and diff-tool pitfalls).

Broader cross-source / rebuild / instrument-traps wards live in
`references/cross-source-and-rebuild-verification.md`. Three high-value rules from it,
applicable to nearly every multi-source audit:

- **Byte-identical values on two supposedly-independent sensors is MORE suspicious than a
  close-but-not-equal match.** Before calling cross-source agreement "corroboration," match
  BY CONTENT (durations, per-stage minutes, window edges), not by provenance — a handoff
  record found in both stores is usually one measurement ingested twice via a sync/import
  path. A "±2h difference" that equals a whole-hour timezone offset is a re-labeling of one
  instant, not a sensor difference.
- **Never trust a timestamp column name.** `*Gmt` / `*UTC` fields in consumer-device
  exports sometimes hold local-display time — and sometimes they mean exactly what they
  say after you'd convinced yourself otherwise. Validate semantics ONLY with mechanical
  anchors (never field names, never another column whose own convention is unproven):
  (a) epoch millis in sidecar files; (b) a same-instant multi-device overlap (two
  sensors on one sleeper — frames must agree within algorithm tolerance); (c) user
  testimony on known event times (wake times); (d) downstream-impossibility tests — if
  one reading makes sleep→workout gaps go NEGATIVE for dozens of rows, that reading is
  dead; (e) **DST seasonal-median test** (sharpest, DST regions): winter-vs-summer
  medians of the raw string column shift ~±1h iff strings are UTC (fixed local
  schedule + moving local offset), ~0h iff strings are local — measured +1.13h in the
  worked case. Reading a local-labeled field as UTC (and re-re-reading it back) shifted
  an entire decade narrative 2–3h here. All five anchors + the peer-review loop:
  `references/timestamp-frame-discrimination.md`.
- **A verbatim import-copy is not an anchor.** A minute-identical record found in two
  stores (source + importer) proves the IMPORTER assumed the source's convention — not
  that the source emitted it. Cross-source "corroboration" via a sync/import path is
  circular; match by content across genuinely independent sensors instead. (Flagged by
  peer review after I'd cited it as proof.)
- **"Tool X runs" is a claim to re-run, not inherit.** A prior session's "ran every script
  verbatim" can be false — two committed tools crashed as-is (sqlite `ATTACH ...` needs
  `uri=True` on the main connection). Re-execute the committed artifact yourself.

## Verify the script, then run it read-only

1. **Read the producing script line by line before running.** Note exactly what it
   computes (filters, windows, units, divisors). `statistics`-style pitfalls hide here.
2. **Replicate the SQL yourself under a read-only connection** rather than trusting the
   script's connection. Python: `sqlite3.connect('file:/abs/path.db?mode=ro', uri=True)`.
   ATTACH extras with `...?mode=ro&immutable=1` so no `-wal`/`-shm` sidecars are created.
   If the script's main connection omits `mode=ro`, flag it — posture inconsistency even
   if it only SELECTs.
3. **Re-derive, don't re-read.** Build your own query for each headline number; compare
   to the claim's table. Mismatches = the actual finding. Matches = confidence, but still
   check framing (below).
4. Before trusting a cross-source/joined number, confirm no NULL-key rows silently drop
   (a `NOT(cond)` predicate yields NULL for NULL rows, excluding them from BOTH sides).

## Sequence: your SQL first, their script second

When the claim came from a script that still exists, resist running it first — its
output anchors you. Order: (1) transcribe the published numbers into a claim table
BEFORE reading the script's output; (2) write and run your own SQL; (3) only then run
their script verbatim and three-way diff: **published vs my-SQL vs their-script**.
their-script ≡ my-SQL ≠ published isolates a transcription/reporting defect in the
doc; my-SQL ≠ their-script isolates a computation difference (units, filters,
divisors, window edges).

## Diff-tool pitfalls (self-caught)

- **Absent-value cells.** A tool's stdout may print `None` where a metric doesn't
  exist (e.g. deep sleep in years with no staged nights). A diff parser doing
  `int(cell)` crashes there, and the parse error masquerades as a data defect.
  Tolerate absent cells explicitly; flag only true asymmetries (their None vs your
  number).
- **Integer-stated bands.** Prose bands like "median 17-18 min" are rounded claims.
  Compare `round(your value)` to the band, not the raw value (18.35 vs "17-18" is a
  false defect; 18 is a match). Report residual off-by-one band edges as minor prose
  defects WITH a conclusion-impact verdict (usually "collapse conclusion unaffected").
- **Rounded published integers.** Match within 1% relative OR an absolute tolerance
  sized to the publish rounding (published 96 vs re-derived 95.7 is a match;
  demanding exact equality on a rounded integer manufactures noise).
- **"No data" claims are countable claims.** "n/a (no stages)" / "no records in
  window" is verifiable the same way as a number: count qualifying rows in the window
  (e.g. `has_stages=1` → 0 of 63 nights confirms it). Verify absence, don't skip it.
- **Row count ≠ reading count.** Snapshot-style tables can carry duplicate rows
  (e.g. 15,973 rows but 8,751 distinct readings); dedupe by (timestamp, value)
  before trusting any count derived from them.

## The sharpest pitfall: SQL boolean precedence

`WHERE A OR B AND C` parses as `A OR (B AND C)` — the trailing `AND` scopes to ONLY the
last `OR` term. If `A` is intended to be filtered by `C` too, the `A` rows come back
UNFILTERED. Signature: a yearly-window query returns ~the same large count every year
(e.g. exactly the count that the unscoped branch matches alone).

- Symptom I hit: "conscious AND date-window" with the conscious predicate written
  without outer parens silently returned all conscious rows regardless of year.
- Fix: always wrap compound predicates — `( ... OR ... ) AND window`. Or, in Python,
  build the predicate as a single parenthesized string: `(exercise_type IN (…) OR (… AND …))`.
- Guard every OR'd condition. Test the query on a year you KNOW should be empty of data
  (here: a year before the dataset starts) — if it returns rows, the predicate is unscoped.

## Second sharpest pitfall: one metric, dual "lineages" across tools

Two scripts can implement the SAME conceptual definition differently, and each re-derives
correctly under its own variant — a "lineage" mismatch, not an arithmetic error. Worked
case (see `references/lineage-dual-night-key.md`): a raw `start_local -18h` "night key"
was implemented in one tool as `datetime(start_local,'-18h')` (keeps late-evening starts
on the same calendar day) and in another as `date(start_local,'-18h')` (always the prior
day). Every record's key shifted by −1 day between tools, so a seasonal-control table and
the main per-draw table cited the SAME metric as 73 *and* 72, and the control value (63)
only reproduced under the *producing* tool's lineage (the other lineage gave 60).

- **To claim a match, re-derive under the producing tool's exact lineage** — not just the
  "documented" definition. Read the actual implementing expression, replicate THAT.
  A number that matches the doc only under the doc's stated-method lineage but not the
  producing script's is still a tool/doc inconsistency worth flagging.
- **When a metric appears twice in the same doc with different values, trace each back to**
  **which tool/expression produced it** before calling it an error — it's often two lineages.
- **Report the lineage explicitly** on lineage-sensitive numbers (e.g. "63 reproduces only
  under seasonal_control's date()-18h night-key; under the documented datetime()-18h it is
  60"). This makes the defect the *fixable* one: standardize one definition everywhere.
- Unit/normalization differences (UTC vs `localtime` date bounds, per-hour vs per-night
  averaging) are usually minor at the edges — quantify the impact (e.g. 58.9 vs 58.85) and
  note it, don't treat it as a match failure.

## Time-of-day / circular-metric pitfalls (bedtime, night-key style metrics)

Re-deriving "minutes-after-X bedtime" metrics generates its own failure classes. Worked
case in `references/sleep-bedtime-extraction-audit.md`.

- **Verify a wrap formula equals the circular mapping before trusting it.** A bed-time
  formula like `m - 1080 if m >= 1080 else m + 360` is *mathematically identical* to
  `(m - 1080) % 1440` for **every** input (incl. a 17:30 local start → 1410). Consecutive-if
  wrap code is almost always a correct full-day circle — don't call it a bug on sight.
  Independently recompute `(m-offset)%1440` on sample nights to confirm equality.
- **The real defect is the missing WINDOW GUARD, not the arithmetic.** The docstring may
  promise an intended range (e.g. 18:00–06:00 → bed 0..720) while the formula happily
  returns out-of-window values (720..1439) for session starts in 06:00–17:59 local
  (daytime/nap/mis-keyed sessions). Count out-of-window nights; they can be a tiny share
  of the dataset yet CLUSTER in one month and shift that month's median materially
  (observed: 8/1336 nights all in 2018-03, bedtime median <value>→<value>, +50 min). A 0.7% outlier
  rate is invisible at year granularity but not within a single month.
- **min-over-fragments ≠ min-reclock-then-wrap (the subtle re-derivation bug).** When the
  producer takes `min(bed(fragment))` = `min((m-1080)%1440)` over a night's fragments, you
  must re-derive the SAME expression — do NOT compute `(min(m)-1080)%1440` (min clock time
  THEN wrap). These differ whenever a night has fragments on both sides of midnight and
  produced a FALSE mismatch here (339 vs true 330) until corrected. `%` doesn't commute
  with `min()`.
- **Infra bug: month-key slicing vs dash. `'2019-06-30'[:6]` is `'2019-0'`, not `'2019-06'.`**
  If keys are ISO dates, slice `[:7]` or split on `-`, not `[:6]`. Two probes I wrote
  silently emptied their month samples with the wrong slice length.
- **DST probe: convert a full winter month + a full summer month, don't spot a single day.**
  Verify `utc → local` gives offset +2 (EET) and +3 (EEST) on many nights each, and confirm
  cross-midnight `calendar_date == wake_date` handling. A single-day spot check misses rolloff.

## Mechanical guard: trust no tuple, bind before you diff

Before concluding MISMATCH on a re-derived helper, verify your unpacking of its return
tuple matches its `return` order. This session a `(nights, deep, wake, dur, rows)` helper
was unpacked onto the wrong variables, so the re-derived "median" came out as the raw
night count and printed a false MISMATCH; the true median (72) was sitting in the next
slot. When a number "mismatches," sanity-check it against an adjacent known value (wake=34,
dur=6.81h lining up with the doc) before declaring a defect.

## Frame-check the number, not just the arithmetic

A correctly-computed headline can still mislead via framing. Audit all of these:

- **Base/baseline choice (cherry-picking).** A "ROSE 2.6× YoY" may compare against the
  weakest prior year (a dip), where "vs the year before that" = 1.73×. Always recompute
  against the next-best baseline and report the range.
- **Definitional drift / asymmetry across sources.** A variable's definition that changes
  at a device/data-source handoff can manufacture a trend. Check whether the "before" and
  "after" populations are comparable. If the headline is interior to ONE source (e.g.
  Samsung-vs-Samsung), it's immune to the handoff confound — state that explicitly; it's
  the strongest kind of evidence.
- **Cross-source comparisons ("record since 20XX").** If the superlative spans a device
  change, note the sets are only "same order of magnitude", not exactly comparable.
- **Noise inclusions.** A "keep minor sessions in tier-1 + note them" choice can be fine
  (verify the actual max impact — often negligible), but it must be a stated judgment, not
  silent.
- **The headline the author wanted vs the headline the data shows.** If the claim is
  literally true but the story is stronger than the series supports (up-down-up ≈ "steady"
  not "rising"), say so.

## Read-only / workflow discipline

- Never write to the repo or source DBs during an audit. Scratch live in `/tmp` only.
- Write audit scripts via `write_file` and run them as files — heredoc/redirect writes
  are approval-gated in this environment.
- Probe NULL-key counts and note them as fragility even if currently zero.

## The verifying tool itself needs auditing (2026-08-30)

Building NEW verification tooling (a cross-patcher, a gate suite, a watchdog) is itself a
claim to audit — the checker can be WRONG in ways that make it silently useless or
permanently broken. Every item below was a real bug in a shipped verifier caught by a
SECOND review scoped to the verifier itself (the first review, scoped to the collector,
passed clean).

- **A verifier can be dead code.** A body-composition "cross-check" picked `next()` = the
  FIRST snapshot (HC-first, no export row), so the ONE snapshot that HAD export truth was
  never exercised — the printed "CHECK OK" was true of the wrong row. Fix: iterate ALL
  candidate datapoints and cross-check each against export by explicit key; then RUN it and
  confirm it fires on a real paired row. A fix can be syntactically correct yet dead
  (`'weight' in body` on a dict keyed by `(metric,time)` tuples → always False → still
  nothing checked).
- **A failing gate is a catch, not a bug to suppress.** A phys-band gate (staged minutes ∈
  [180,720]) caught a cross-payload sleep-dedupe bug on first run (nights summed 6× from
  re-served sessions). Diagnose WHY data violates the gate and fix the data path — do not
  widen the gate to make the check pass.
- **In-memory dedupe is not a durable guard.** If dedupe is a set keyed on a value, a
  regression silently multiplies rows while value-range gates still pass. Enforce at the
  schema too: a `UNIQUE(start_utc,type)` constraint + a gate that row-count == distinct
  source-key counts.
- **Perpetually-failing gates hide real divergences.** An all-or-nothing verdict that never
  tolerates documented-by-construction diffs (e.g. the export's trailing PARTIAL hour bin —
  only part of the hour was ingested) fails on EVERY run forever, drowning genuine diffs in
  noise. Tolerate the known-benign case so the gate returns green and only real diffs flip
  it.
- **Reachability is not "HTTP 200".** A watchdog that treats non-200 as "source unreachable"
  false-alarms when the host returns 404 for a route it doesn't serve. Reachability = the
  TCP connection succeeded (ANY HTTP response, including 404); only a connection failure
  (timeout/refused/DNS) is "down". Status code is a separate concern.
- **Mixed-granularity summing.** Some series serve both a full-window AGGREGATE and in-span
  DELTA windows (steps: a full-local-day total + finer windows inside it). Summing = double
  count. The total = the midnight-anchored FULL-DAY window only; classify windows by span
  (≥23 h = day) and reject deltas for day totals.
- **Second review must be scoped wider than the first.** Validate the verification LAYER
  (parse→DB→gates, the verdict/exit logic) as a separate object, not just its inputs. The
  cross-patcher's own dead-check bug lived in the function that was supposed to prove it.

## Deliverable

Output a tight, structured report: **Verified Facts (literal outputs)** → **rule/claim
vs re-derived table** → **findings** (🔴 blocking / 🟡 framing-or-caveat / 🔵 confirmed)
with file:line → **unverified items** → **confidence**. Lead with outcomes, bullets, not
your process. For durability, file the full re-derived rule table + SQL pitfall as a
`references/` file under the governing domain skill.

---

> **Folded in from the former `data-claim-verification` skill.** It is a worked checklist for the
> same job `evidence-loop` performs — verify a number before it becomes standing advice — so it
> now lives here as the reference form rather than as a separate skill.
