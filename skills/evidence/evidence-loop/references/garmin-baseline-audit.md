# Worked Example 2: Garmin Jul-Sep Baseline Table (It2 re-derivation)

Session: PR #6 verification loop, iteration 2 (2026-08-16). Task: personally re-derive
every number in the "Garmin-era Jul-Sep baselines" table of
`health.health_dir/samsung-data/pre-draw-window-findings.md` before trusting it — deep medians,
RHR means, run/ride counts, modality hours, and two prose claims.

## Setup (durable facts for re-runs)

- DB: `$HERMES_HOME/data/garmin.db` — tables `workout(1263)` `sleep_night(1898)`
  `daily_summary(1900)` `fit_session(1263, FIT-arbitrated ground truth)`.
- Window: `>= 'YYYY-07-02' AND < 'YYYY-09-03'` — 63 days = exactly 9.0 weeks
  (watch the divisor: an earlier script's divisor inflated min/wk,
  self-caught and retracted in the doc).
- `sleep_night.calendar_date` = WAKE date; `has_stages=1` gate for deep medians.
- `rhr_snapshot`: 15,973 rows but only 8,751 DISTINCT readings — dedupe by
  (ts_utc, resting_hr) for any distinct count.

## Method that worked (all 5 years × 5 metrics reproduced)

1. Transcribe published table → claim dict BEFORE running anything.
2. Own SQL per year: deep median over `has_stages=1` nights; RHR mean from
   `daily_summary`; run/ride counts + medians + ≥30-min splits + duration buckets
   (<15 / 15-30 / ≥30); `sport_group` hours; total-min/9.0 per week.
3. THEN run their script verbatim; three-way diff published vs mine vs theirs.
4. Classify: MATCH / MATCH-within-rounding / MISMATCH with % and severity.

## Results (matches within rounding unless noted)

- min/wk: 96/223/330/248/177 → re-derived 95.7/222.6/330.1/248.4/176.8.
- Deep medians (staged nights): 207 / 212 / 229 (n=63/63/62 staged).
- RHR means: 46.83 / 45.44 / 45.18 / 43.64 / 45.91 (all n=63 days).
- Run counts 14/6/10/15/9 exact; hard sessions 14/10/2/1/4 exact.
- Modality hours all matched (2017 gym 12.9h, hike 10.1h; 2018 ride 23.9h; etc.).
- "69 short rides 2018" ✓ — 69 rides, distribution 1 / 67 / 1 across buckets
  (<15/15-30/≥30 min) — "mostly short" framing accurate.
- "2016 no stages" ✓ — 0 of 63 nights have stages (2017 also 0; doc's n/a correct).

## Defects found (both minor prose, table itself clean)

1. Run-median band edge off by 1: 2016 actual 30.45 (pub "31-35"); 2018 actual 15.56
   (pub "17-18"). Cause: prose bands rounded without re-checking; collapse conclusion
   (run-median bands) unaffected. Doc fix: bands → "~30-34" and "~16-18".
2. Diff-parser bugs I introduced and fixed in the evidence script: `int()` crash on
   `None` deep cells for 2016/2017; false MISMATCH from comparing 18.35 unrounded
   against integer band "17-18". See SKILL.md "Diff-tool pitfalls".

## Evidence-script shape (reusable template for claim tables)

`published` claim dict (from doc, verbatim) → `rederived` (own SQL, read-only
connections) → `their_script` (verbatim run, stdout+rc) → `match` verdicts with
relative-% or abs tolerance sized to publish rounding → `defects` list where each
entry carries severity + impact-on-conclusion. Verdicts include prose-band checks
(rounded) and countable absence claims ("no stages" = count rows = 0).
