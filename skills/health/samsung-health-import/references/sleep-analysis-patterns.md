# Deep-Sleep Pattern Analysis — Drivers & Query Pitfalls (2026-08-15)

Companion to `sleep-analysis-findings.md` (which covers wake-time/era methods and the lived-clock rule — read that first for era questions). This file: what drives deep sleep, and the schema/display traps specific to pattern queries.

## Verified deep-sleep drivers (6-month window, n=168 nights, night-key grouped)

- **Deep ≥50min is the NORM (60% of nights).** Frame analyses as "what separates the bad 40%", not "what's special about good nights" — the base-rate inversion changes the question.
- **Running is the only modality that separates good from bad nights**: run minutes 10.6 vs 3.7/day (good vs rest); P(deep≥50) = 78% on run days vs 57% non-run. Walk (64.5 vs 60.3), gym (19.4 vs 21.6) minutes are IDENTICAL between groups.
- Modality gradient (dominant activity → that night's deep): run 68min (14.6%) > e-bike-commute days 61 (14.8%) > walk 54 (12.6%) ≈ gym-strength 53 (12.3%). NOTE: the pre-correction analysis mixed 11007 populations — "cycle 61" and "gym 57" rows contained e-bike commutes (Stockholm, no distance) + auto-fragments, NOT regular cycling (zero Stockholm distance-rides exist) — treat per-modality numbers from that pass as approximate; the ordinal conclusion (locomotion > non-locomotion) is unaffected.
- **Gym-strength days (type 15002) do NOT enrich deep sleep** — deep 53min/12.3%, indistinguishable from walk-only days. Sustained locomotor/aerobic work (run 68min/14.6%, e-bike-commute days 61min/14.8%) is the lever, not intensity and not strength training. (Labels testimony-corrected 2026-08-15: 15002=gym strength, NOT a group class.)
- **REM is decoupled from deep** (113 vs 109min good vs rest) — no stage tradeoff; deep doesn't displace REM.
- **No rebound/banking**: d±1 deep/REM show no repayment after good or bad nights.
- **Dose saturates**: biggest day (82min/15km run + gym) → 58min deep = average run-night. Ceiling, not linear. Don't promise "more running → more deep".
- Confound to state with any run-day claim: run days are also longest nights (7.82h vs 7.2h); deep % still rises (14.6 vs 12.7) so the effect survives duration control partially, not fully.
- Evening sessions don't block good nights (gym session ending 20:00 → 56min deep observed).
- Weekday spread of good nights was flat (12–17 per day-of-week) — day-of-week is not a deep-sleep factor for this user; don't chase it.

## Query & display pitfalls (each bit us once)

- Query the **`sleep_stage_named` view** (column `stage`: awake/light/deep/rem), not `sleep_stage` (column `stage_code`).
- `workout.duration_s` is SECONDS. Any human-facing display must `/60` — one readout shipped "run:2959min" (actually 49min) and the user had to ask for the fix. Check display units of every derived field before presenting.
- RAW Samsung fields (`duration`, `total_sleep_time`, sleep-table stage durations) are MILLISECONDS — only parser `*_s` columns are seconds.
- Night-key grouping on `start_local` works; raw calendar-date grouping splits nights at midnight (phantom 11.7h nights from 03:30 fragments).
- `hrv_window` rows are HOURLY windows — nightly RMSSD = AVG(rmssd_mean) over windows inside sleep sessions, never one-row-per-night.
- One 1970 placeholder HRV row exists — skip timestamps <2020 in any HRV aggregation.
- SQL julianday minute-diffs: CAST to INT before comparing to literal minutes (float 59.9999 ≠ 60 broke a tz histogram).
