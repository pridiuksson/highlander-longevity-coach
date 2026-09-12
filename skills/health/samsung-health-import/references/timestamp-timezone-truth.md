# Timestamp & timezone ground truth (Samsung + Garmin exports)

Settled 2026-08-16 after a full-day frame inversion hunt. This file is the
proof chain; the operative rules live in `SKILL.md` and the runbooks
(`health.health_dir/samsung-verified-data.md`, `garmin-verified-data.md`).

## Samsung: ALL CSV time strings are TRUE UTC

Claim: every `com.samsung.health.*.csv` time column (`start_time`,
`end_time`, `update_time`, …) holds a **UTC naive string**, and the
`time_offset` column (`UTC+0300`) holds the **local offset**.

Correct conversion:
```
utc   = string, as-is
local = string + offset
```

Mechanical proof (the epoch arbiter): sidecar JSONs shipped in the export
zip carry absolute ms epochs that are independent of any column-label
interpretation:

- `jsons/com.samsung.shealth.exercise/<hex>/<datauuid>.liv` —
  `"start_time": 1744865076251` = 2025-04-17 04:44:36 UTC, byte-equal to the
  exercise CSV string for the same row.
- `jsons/com.samsung.health.*/…​/sleep_status.json` / `binning_data.json` —
  epochs match sleep/HR CSV strings for the same sessions.

The original parser assumed the strings were LOCAL and subtracted the
offset (`to_utc`) — producing a double-subtracted `start_utc` and a
UTC-mislabeled `start_local`. Both columns were wrong in every family
(exercise, heart_rate, sleep_session, sleep_stage). Fixed in
`parse_samsung_export.py` (`to_utc` = as-is, added `to_local` = +offset,
added `end_local`); DB rebuilt, all parse gates re-passed.
Post-fix `$HERMES_HOME/data/health.db` md5: `638da6ad…` (pre-fix `cb67d879…` is obsolete).

Behavioral confirmation: post-fix, the 2025-04-17 morning abs session reads
07:44:36 LOCAL (user: mornings, post-6:40-wake); night wakes read 06:37
(user: ~6:40). Pre-fix readings put wakes at 04:xx — impossible.

## Garmin: sleep `sleepStart/EndTimestampGMT` are TRUE UTC

Four independent mechanical anchors (2026-08-16 evening, peer-reviewed):

1. **Overlap week**: night in the 2021-08 handoff week, both devices worn — Garmin string
   21:42 vs Samsung-native (epoch-proven UTC) 22:18: 36 min apart, two
   algorithms on one sleeper. Local reading implies Garmin detects sleep
   3h36m BEFORE the other wrist — impossible.
2. **Wake testimony**: UTC reading → wakes 06:45–07:45 local; matches the
   reported ~06:40–08:00 pattern. Local reading → 04:xx wakes.
3. **Workout-gap**: first-workout-after-sleep-end gap, n=228 nights
   (workout times epoch/GPS-proven UTC independently): median +1.48 h under
   UTC reading; **negative** under local readings (workouts before sleep
   ended — impossible).
4. **DST discriminator** (immune to watch-clock state): Vilnius +2↔+3 flip
   must shift string wake medians ~+1 h seasonally if strings are UTC, 0 h
   if local. Measured **+1.13 h** (summer 06:16, winter 07:23; n=361/346).
   Script: `health.health_dir/decade-sleep/tz_dst_discriminator.py`.

Field name `TimestampGMT` meant what it said. Local = stored + 2h winter /
+3h summer (EET/EEST, Vilnius era).

Recorded negatives (tests that could NOT discriminate — kept so nobody
re-runs them hoping): RHR-in-window containment (13.2% vs 10.0% — all-day
sampling makes it mushy); RHR circadian trough (near-flat 46.7–48.<YOUR_RESTING_HR_BPM>).
Also circular, hence worthless: the healthsync import row being
minute-identical in Samsung's UTC column (proves the importer's assumption,
not the source's semantics).

## General rule

Settle every timestamp-convention question with a **mechanical anchor**
(absolute epochs in sidecars, same-instant cross-device measurements,
DST seasonal shifts, impossible-ordering tests). Never from field-name
semantics, never from another column whose own convention is unproven,
never from plausibility. All three of this session's misreadings came from
label/plausibility reasoning; every correction came from an anchor.

## Where the numbers live

- Runbooks: `health.health_dir/samsung-verified-data.md` (tz sections),
  `health.health_dir/garmin-verified-data.md` §Sleep timestamp semantics.
- Evidence scripts: `health.health_dir/decade-sleep/tz_dst_discriminator.py`,
  `tz_overlap_anchors.py`, `tz_probe.py`.
- Decade consequences (bedtime narrative): `health.health_dir/decade-sleep/README.md`
  correction history items 2 & 5.
