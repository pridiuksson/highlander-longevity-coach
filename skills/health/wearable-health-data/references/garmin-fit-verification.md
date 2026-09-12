# Garmin FIT ground-truth verification (verified 2026-08-16)

Read-only, independent re-derivation of the FIT parser's ground-truth claims from
`$HERMES_HOME/data/garmin.db` (does NOT depend on re-running parse_garmin_fit.py).
Reproducible numbers for future checks / sanity gates.

Scope: `<YOUR_HEALTH_DIR>/garmin-data/parse_garmin_fit.py` + the
`fit_session` / `rhr_snapshot` / `fit_progress` tables it produces.

## Workout ↔ FIT session join

Both tables have 1263 rows, all with non-null `start_utc`.

Time-only join `ABS((julianday(f.start_utc) - julianday(w.start_utc))*86400.0) <= 300`:
- workouts with EXACTLY ONE match: **1263**
- workouts with ≥2 matches: **0** ; with 0 matches: **0**
- fit_sessions matched by ≥1 workout: **1263/1263** (each by exactly 1)
- **max |diff_s| over all 1263 pairs = 0.0s** → the join is EXACT to the second,
  not merely "within ±300s". The tolerance window is a red herring: start_utc
  equality is the real arbiter.
- distinct start_utc on each side = 1263 (no degenerate duplicate-timestamp join).
- smallest gap between distinct fit_session starts = **516s** (2016-09-11 11:57:<value>→<value>:05:51) — larger than the ±300s window, so interval-workout collisions are
  impossible even if timestamps were merely near rather than exact.
- Reverse idempotency check: `DISTINCT fit_file` in fit_session = 1263 (one
  session row per file).

## Unit-arbitration numbers (corrected JSON vs FIT ground truth)

- pairs with BOTH `distance_m` non-null AND FIT distance > 0: **785** = the "n=785".
- The other 478 matched pairs are `gym` with FIT `distance = 0` (JSON still carries
  a distance) — don't compute the ratio on those.
- Raw `fit/json` distance ratio: min=median=max = **0.010000** on all 785 rows
  (exactly 100× inflation in JSON).
- Corrected-JSON (stored dist = json/100) vs FIT: rel diff median 1.72e-08,
  max 5.67e-08 (= float rounding), exact (==) in 107/785 — two independent sources.
- Speed: FIT vs stored `avg_speed` (= json×10): rel diff median 1.94e-08, all 785 <1e-6.
- mean_hr (JSON) vs avg_hr (FIT): **exact in 1250/1250** pairs.
- Post-fix sane maxima: ride 42.4km, run 10.2km, walk 7.0km, hike 11.8km, swim 1.37km.

## rhr_snapshot semantics

- `monitoring_hr_data` message carries ONLY {timestamp, resting_heart_rate,
  current_day_resting_heart_rate} — confirmed via fitdecode field-count on 5
  monitoring_b files (1–3 such messages/file; the dense `monitoring` HR messages
  are correctly ignored by the parser). Snapshot data, NOT continuous HR.
- **15,973 rows = only 8,751 DISTINCT (ts, resting, current_day) tuples.**
  14,048 rows (88%) are the same reading repeated across up to 5 monitoring files —
  Garmin re-emits each RHR reading into every day's monitoring_b file. Dedupe
  (DISTINCT per day) before treating 15,973 as a reading count.
- resting_hr: min 41, med 47, max 66, none >80, none <35, none NULL.
  current_day_resting_hr: 1872 NULL, 2 >80, 12 <35 (both plausible at <YOUR_RESTING_HR_BPM> edge/-).
- Range 2016-05-23 → 2021-08-26 (1922 days) ≈ 8.3 rows/day → snapshot cadence.
- 73 monitoring_b files have ZERO rhr rows — legitimate (contain only `monitoring`,
  no `monitoring_hr_data`); not a parse bug.

## Method notes (reusable)

- `sqlite3` CLI not installed on this box → use `python3` + `sqlite3` stdlib.
- Open read-only: `sqlite3.connect(f'file:{DB}?mode=ro', uri=True)`; never hand-join
  raw tables across two DBs — use the ATTACHed `queries.py` path.
- fitdecode lives only in `.venv` → `.venv/bin/python` for any FIT inspection.
- Re-derive joins from stored timestamps directly (read the max/true diff), don't
  re-trust the parser's stated window — the stored data often matches tighter.
