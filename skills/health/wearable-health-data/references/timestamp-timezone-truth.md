# Samsung Health CSV Timestamp Timezone — TRUE UTC (epoch-proven)

**Verdict (2026-08-16, epoch-anchored, resolved via subagent deep-dive in
`health.health_dir/`):** every Samsung Health 2026-format raw CSV
`start_time` / `end_time` string is a **TRUE UTC naive** — NOT local. This applies
uniformly to exercise, heart_rate, sleep session, sleep stage, sleep_data, and
hr_threshold alike. The `time_offset` column ('UTC+0300') records the LOCAL offset.

## Why the old parser was wrong
`parse_samsung_export.py` `to_utc(local_str, offset_str)` treated the CSV string as
LOCAL and SUBTRACTED the offset to get UTC. Since the strings are actually UTC:
- what it stored as `start_local` = TRUE UTC (value right, label wrong)
- what it stored as `start_utc`   = true-UTC − offset (double-subtracted)
Both columns are wrong for every timestamp family.

## The correct conversion
- `utc   = raw string (parse literally, no subtraction)`
- `local = raw string + offset`  (offset '+' means local is AHEAD of UTC)
- Equivalently from the current mis-parsed DB: `fix_utc = current_ts_local`,
  `fix_local = current_ts_local + offset` = `current_ts_utc + 2×offset`.

## Three independent epoch anchors (all string == true-UTC instant)
1. **Exercise**: CSV `start_time '2025-04-17 04:44:36.251'` == sidecar
   `jsons/com.samsung.shealth.exercise/<hex>/<uuid>.liv` epoch `1744865076251`
   → `2025-04-17 04:44:36 UTC`.
2. **Heart rate**: each `binning_data` JSON's first/last bin epochs convert to UTC that
   EXACTLY equals the CSV `start_time`/`end_time` string (verified across many months,
   e.g. CSV `2026-04-05 01:00:00` ↔ bins `01:00–01:59 UTC`). Binning JSON lives at
   `jsons/com.samsung.shealth.tracker.heart_rate/<x>/<uuid>.com.samsung.health.heart_rate.binning_data.json`,
   a list of `{start_time, end_time, heart_rate, ...}` in ms epochs.
3. **Sleep**: sleep_data / `sleep_status` JSON
   (`jsons/com.samsung.shealth.sleep_data/<x>/<uuid>.sleep_status.json`, a list of
   `{"status", "start_time":<ms>, "binning_period":10}`) epoch `1631057760000`
   → `2021-09-07 23:36:00 UTC` == that session's sleep CSV `start_time '2021-09-07 23:36:00.000'`,
   and that is the SAME record as the `sleep_session` row (shared sleep_uuid/datauuid).
   So sleep_session is the same UTC series. Sleep_stage rows for a session span exactly
   the session's UTC bounds (identical offset col + string format), so stages are the
   same UTC frame; summed stage duration == session duration to the second.

## Behavioral corroboration (abs-program week)
Night 2025-04-16..17 sleep session `57fe132d` reads `start 21:26 → end 03:37`
(offset +0300). As UTC: wake = 06:37 Vilnius local (EEST) ≈ the user's ~06:40 wake, and
the morning abs workout at `04:44 UTC = 07:44 local`. As local it'd read wake 03:37 —
disjoint from the user's stated wake + morning-workout testimony.

## Garmin 2021-08-25 handoff exception (the ONLY non-UTC row)
`datauuid 64b3820f`, pkg `nl.appyhapps.healthsync`, offset `UTC+0200` — a night
**imported into Samsung from Garmin Connect by the healthsync app**, not recorded by
Samsung's detector. Its `'2021-08-25 23:28'` string is **local-display** (= Garmin's
local display), which is why it matches the Garmin row to-the-minute. Keep it excluded
from Samsung-native sleep stats (Garmin-side data in a Samsung wrapper), as
`health.health_dir/garmin-verified-data.md` already instructs. This is why an earlier
"sleep differs from exercise" hypothesis looked plausible — it was reading this one
importer-written row.

## Repair note
Fixing existing DB rows is a data-migration task (rebuild via a corrected parser with
`utc = raw`, `local = raw + offset`). The anchors are recorded here; do not re-derive.
