# Enrichment parser layer — verified 2026-08-29 (Samsung Health, this pipeline)

Post-core ingestion layer for `<YOUR_HEALTH_DIR>/samsung-data/` (runbook:
`samsung-verified-data.md`, findings 11-12; IMPORT_PLAN.md is the plan-of-record).
All parsers: dynamic filename resolution, fail-loud resolve(), idempotent
(drop+recreate or ADD COLUMN if missing), gates mandatory before any advice.

## MapMyRun aux-merge (`merge_mapmyrun.py`, gates M1-M5)

52 rows carry `pkg_name=com.mapmyrun.android2`, exercise_type 1002, NO HR
anywhere. USER-CONFIRMED semantics: aux dual-recordings of real runs (bluetooth
shoe cadence), NOT duplicates, NOT phone-only runs. Do not delete them.

- Join: same calendar day + |start delta| ≤ 30 min → 46/52 pair (median delta
  25 s, duration ratio 1.019, distance Δ −2.7%).
- Shoe-vs-watch cadence: median Δ −0.63 spm, 36/46 within 2 spm — independent
  sensor validation, usable as a cadence-truth cross-check.
- 6 unpaired rows: 1 real solo run (4.08 km, 2025-04-12) + 5 sub-km app stubs.
- Output: `workout_run_merge` + `workout_mmr_solo` tables and view
  `v_workout_runs` = 184 physical runs (230 raw = 178 watch + 6 solo).
  **Run counts / weekly distance MUST use this view**, never raw 1002 rows.
- Attribution lesson: "phone-GPS runs" was inferred from signal shape and was
  WRONG twice — `pkg_name` settles provenance in one query. Check provenance
  fields (pkg_name, source_type, deviceuuid, heart_rate_deviceuuid) before
  telling the user what a row class is.

## Recovery-HR decay curves (`parse_samsung_recovery.py`, gates R1-R7)

- Source: `com.samsung.shealth.exercise.recovery_heart_rate.<stamp>.csv`
  (exercise_id → workout.datauuid) + curve JSONs named by the RECORD datauuid —
  a TWO-HOP join; curve files do not match workout uuids directly.
- Payload: `{chart_data:[{elapsed_time, heart_rate, start_time}], is_valid,
  sampling_rate}`; 175 valid ~120 s curves (20,579 points), 11 empty/invalid
  → `recovery_hr_skipped` (count rows ≠ count valid payloads; gate the payload).
- Tables: `recovery_hr_summary` (hr_start/hr_60/hr_120/drop_60/drop_120, NULL
  drop_120 for the 1 short-window curve), `recovery_hr_point` (1 Hz).
- Curves start median 0.6 s after workout end. Curve hr_start outranks stale
  summary max_hr (one workout: summary 165 vs curve 171, NO sidecar exists).
- Semantics: runs hold drop_120 ≈ <YOUR_RESTING_HR_BPM> since 2022; all-workout year series
  (18/10/34/32/34) is a workout-MIX effect — never read as fitness trend.
  Session-level reads (hill run 2026-08-23: <value>→<value>, drop 82 vs p90 52) are
  the actionable signal.

## Sleep-scoring backfill (`parse_samsung_sleep_scores.py`, gates S1-S6)

- sleep.csv carries ~44 scoring columns the core parser drops; backfilled onto
  `sleep_session` (2,173 sessions scored) by datauuid (this one DOES join).
- `sleep_combined_scores` = 245 coaching nights, 38 populated columns (factor
  set, deep/light/REM durations + scores, goal bed/wake, latency, naps).
- sleep_combined rows have their OWN datauuid namespace → time-window join
  ≤6h of session start (245/245). A uuid-equality gate failing 100% means
  namespace collision, not missing data.
- Deep_score/rem_score exist ONLY in the combined table (502/245 rows), only
  2025-2026 era.

## Workout enrichment (`parse_samsung_workout_extras.py`, gates X1-X7)

- +9 columns on workout (22,224 cells): `count` (= exact step count; type 30001
  = steps; cadence×duration ratio 1.000), max_speed, max_cadence, sweat_loss,
  altitude_gain, min/max_altitude, incline/decline_distance.
- `workout_hr_summary`: per-workout hr_mean/max/min from 1 Hz sidecars for ALL
  types — 7,742 rows (6,725 walks, 453 e-bike, 296 gym, 173 runs, 9 BC...).
  Filter `heart_rate > 0` (streams carry 0-dropouts); dense-run hr_mean agrees
  with device summary 140/141 (hr_n ≥ 300 gate); sparse streams defer to summary.
- Byte-level key-presence scans overstate usable data (walk sidecars 98.7%
  contain `"heart_rate"` key but only ~97% have populated values) — gate on
  populated+valid+positive, not key presence.

## Checker protocol that caught the real errors (reuse)

Independent fresh-context checker with: byte-level curve re-derivation (3
curves incl. the anchor), own SQL for every claimed aggregate, and explicit
confound attacks (starting-HR correlation, ≥150-start stratum, drop/hr_start
ratio). It reproduced every number AND still missed the type-mix confound that
a runs-only stratification caught — so: checker for exactness, own stratified
probe for semantics. Both derivations are recorded in finding 11.
