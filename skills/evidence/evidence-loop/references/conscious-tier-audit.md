# Conscious-tier audit — worked example (2026-08-16)

Full worked example of this skill applied to the Garmin/Samsung conscious-tier unification.
Primary artifacts: `health.health_dir/garmin-data/conscious_tier.py` (90 lines), claim in commit
30bbbd5 + `health.health_dir/samsung-data/pre-draw-window-findings.md`.

## Verified facts (read-only, literal outputs)

- $HERMES_HOME/data/garmin.db: 1263 workouts, 2016-06-21 → 2021-07-11, single device_id, median 32.9 min.
  No `rule` ambiguity; 54 workouts <10 min (started-but-trivial), sports = strength 478 /
  cycling 449 / hiking 153 / running 129 / swim 46 / walk 8.
- $HERMES_HOME/data/health.db: 7679 workouts, 2021-08-27 → 2026-07-03.
  exercise_type census: 1001=6785, 11007=320 (38 w/ dist, 282 w/o), 15002=280, 1002=203,
  0=56, 9002=17, 10007=9, 15005=6, 15006=2, 14001=1. 1001 = 88.4% of ALL.
- `exercise_type IS NULL` = 0 and `duration_s IS NULL` = 0.

## Re-derived headline numbers (Jul 2 – Sep 3 windows, ÷9 weeks)

| year | garmin-all (n, min/wk) | samsung-conscious (n, min/wk) | samsung-aux min/wk |
|---|---|---|---|
| 2016 | 33, 96 | – | – |
| 2017 | 53, 223 | – | – |
| 2018 | 116, 330 | – | – |
| 2019 | 75, 248 | – | – |
| 2020 | 39, 177 | – | – |
| 2021 | 3, 11 | 1, 1 (handoff) | 76 |
| 2022 | – | 2, 7 (phone-only) | 818 |
| 2023 | – | 33, 146 | 788 |
| 2024 | – | 27, 98 | 546 |
| 2025 D2 | – | **54, 253** | 277 |

- **2.6×** = 253/98 = 2.577. Samsung-conscious vs Samsung-conscious (same device) → immune
  to device-handoff confound by construction. Best finding type.
- Ambience halved in same windows: aux and auto-walk-1001-alone both fell by roughly half.
- Full 2025 window = 253 proud + 277 ambient = 530 min/wk exactly (the reinterpretation base).
- Frame check: 2.6× is 2025-over-2024, the WEAKEST non-artifact year (2023 was 146) →
  2025-vs-2023 = 1.73×. "Biggest since 2018" (253 vs 248 in 2019) is a cross-device marginal tie.

## The bug that bit me (my own, not the script's)

A re-derivation wrote `conscious AND window` without outer parens on the compound predicate:
`WHERE exercise_type IN (1002,15002,9002) OR (exercise_type=11007 AND dist IS NOT NULL)
AND start_utc >= ...`. SQL parses the `AND ... window` as scoped to ONLY the last `OR` term,
so the `IN(...)` rows were returned UNFILTERED → every year showed n=500 (= exactly 203+280+17).
The script itself is correct because it wraps the whole condition in `( ... )` on line 26.
Lesson → parenthesize every compound predicate and validate on a year that should be empty.

## Tier rule stored elsewhere

Garmin-era all-conscious + Samsung conscious = 1002/15002/9002/11007-with-distance; aux =
1001 auto-walk, 11007 no-dist, type 0, unknown 10007/15005/15006/14001 (never classify).
This domain-specific rule ideally lives under the `garmin-import` / `samsung-health-import`
health skills (protected) — this file is the general method's worked example.

## Follow-up corrections (same-day deep verification, rounds 5-6)

- "D2 beats every non-2018 year by ≥30% under BOTH tier definitions" was **false twice**:
  loose tier 2019 = 248 vs 253 = **+2%**; strict tier unrounded 252.6/194.9 = **+29.60%**
  — a first correction ("+29.7%") inherited the original's rounding error. Lesson:
  re-derive corrections at FULL precision, and state superlatives per tier-variant.
- The +2% loose-tier fact upgrades the frame check above: 2019-vs-D2 is a genuine
  statistical tie (cross-device), so "biggest since 2018" holds ONLY under the strict
  tier-matched variant — which is also the fairer cross-era comparison (tier-symmetric).
- Method file for the six-round audit: `references/pr6-deep-verification.md` under
  `etl-parser-review` (tool-crash, rebuild, validator-coverage, fresh-clone layers).
