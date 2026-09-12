# Garmin account-export zip: tools + format (verified 2026-08-16 via gh api + source reads)

Context: offline parse of the official Garmin "Export Your Data" account zip →
normalize into our star schema alongside $HERMES_HOME/data/health.db. No login, no live API.

## Verdict table

| Tool | Offline-zip | License | Stars | Pushed | Verdict |
|---|---|---|---|---|---|
| arpanghosh8453/garmin-grafana | ✅ | BSD-3-Clause | 3403 | 2026-08-12 | **Winner** — port its zip-walking logic; outputs InfluxDB, not SQLite |
| tcgoetz/GarminDB | ❌ | GPL-2.0 | 3253 | 2026-07-15 | Login/USB import only; schema reference only; GPL viral |
| james-langridge/garmin-export-parser | ✅ | MIT | 1 | 2025-10-16 | TS/JS only; confirms filename patterns; too small to adopt |
| the-momentum/open-wearables | ❌ | MIT | 2343 | 2026-08-14 | Garmin = live Health API (OAuth2+PKCE, webhooks, backfill) |
| cyberjunky/python-garminconnect | ❌ | MIT | 2809 | 2026-08-11 | Live Connect API wrapper (garth auth) |
| matin/garth | ❌ | MIT | 814 | 2026-06-09 | DEPRECATED auth lib. Repo is `matin/` — `mtin/`, `martin/` 404 |

No maintained Python zip→SQLite Garmin specialist exists (checked `gh search code`
DI-CONNECT-FIT + repo searches). Plan: port garmin-grafana parsing (BSD, with
attribution) + fitdecode for FIT monitoring files + own SQLite writer.

## Export zip layout (the DI-Connect tree)

Regexes from garmin-grafana `src/garmin_grafana/garmin_bulk_importer.py`:
- `DI-Connect-Fitness/*summarizedActivities.json` → activities (summary level)
- `DI-Connect-Wellness/*_sleepData.json` → sleep sessions (per-stage durations,
  score); filename `YYYY-MM-DD_YYYY-MM-DD_<userId>_sleepData.json`
- `DI-Connect-Aggregator/UDSFile_*.json` → daily aggregates keyed by
  `calendarDate`: totalSteps, moderate/vigorousIntensityMinutes,
  restingHeartRate, stress durations+percentages (rest/activity/low/medium/high),
  hydration (separate entries). No `sleepingSeconds` — compute from sleep files.
- `DI-Connect-Uploaded-Files/*.zip` → inner zips of per-activity `.fit` files.
  garmin-grafana parses activities only; monitoring FIT messages NOT parsed —
  intraday HR/HRV/stress samples live here and need fitdecode.

garmin-export-parser (TS) patterns agree: `**/*_summarizedActivities.json`,
`**/UDSFile_*.json`, `**/*_sleepData.json`, `**/*Training*.json`.

## GarminDB SQLite schema reference (from garmindb/garmindb/*.py source)

**GarminDB.sqlite** (garmin_db.py):
- `stress`: timestamp PK, stress INT (per-reading, from stress FIT msgs)
- `sleep`: day PK, start, end, total/deep/light/rem/awake (TIME),
  avg_spo2/avg_rr/avg_stress (FLT), score INT, qualifier STR
- `sleep_events`: timestamp PK, event STR (deep_sleep|light_sleep|rem_sleep|
  awake|wake_time), duration TIME
- `resting_hr`: day PK, resting_heart_rate FLT (bpm)
- `hrv` (daily): day PK, weekly_avg, last_night_avg, last_night_5min_high,
  baseline_low, baseline_upper (INT ms), status STR
- also: daily_summary, weight, attributes, device*, file*

**MonitoringDB.sqlite** (monitoring_db.py):
- `monitoring_hr`: timestamp PK, heart_rate INT (continuous)
- `monitoring_hrv_value`: timestamp PK, hrv FLT (RMSSD ms, per-sample in sleep)
- `monitoring_hrv_status`: timestamp PK, weekly_average, last_night,
  last_night_average, baseline_low, baseline_high (FLT ms), status INT
  (0=unknown 2=poor 3=low 4=balanced), reading_count INT
- monitoring_intensity, monitoring_climb, monitoring_respiration_rate,
  monitoring_pulse_ox, monitoring, monitoring_info

**ActivitiesDB.sqlite** (activities_db.py):
- `activities`: activity_id STR PK, name, description, type, course_id, laps,
  sport, sub_sport, device_serial_number, self_eval_feel/effort, training_load/
  effect, anaerobic_training_effect + common cols: start/stop_time, elapsed/
  moving_time (TIME), distance, avg/max_hr, avg/max_rr, calories, cadence,
  speed, ascent/descent, temperatures, start/stop lat/long, hrz_1..5_hr +
  hrz_1..5_time
- activity_laps / activity_splits / activity_records (trackpoints) + sport tables

Grain lesson for our star schema: daily facts keyed by `day` (sleep, rhr, hrv,
dailies); sample facts keyed by `timestamp` (hr, hrv_value, stress); sleep =
one row/day + optional event-level table.

## Techniques that worked

- **Prove absence by grep, not README**: `git clone --depth 1` +
  `grep -rni "DI_CONNECT|account export|GDPR" --include='*.py' .` → 0 hits in
  GarminDB = conclusive no-zip-support (its `zipfile` use is DB backup only).
- **Find parsers by format-marker code search**, not repo names:
  `gh api -X GET "search/code?q=DI-CONNECT-FIT+in:file+language:python" --jq
  '.items[] | "\(.repository.full_name) :: \(.path)"'` — surfaced every real
  Garmin-export parser in one query (garmin-grafana, hlfernandez/garmin-data,
  adam1brownell/garmin_data ★22/2022/no-license).
- GarminDB paths: CLI entry is `scripts/garmindb_cli.py` (NOT garmindb/
  garmindb_cli.py); table defs in `garmindb/garmindb/{garmin_db,monitoring_db,
  activities_db,garmin_summary_db}.py`; importers in `garmindb/garmin_json_data.py`
  and `garmindb/fit_file_processor.py`.

Session artifacts (may be cleaned): $HOME/garmin-eval/ — shallow clones of
GarminDB + open-wearables, garmin-grafana source extracts, FINDINGS_garmin_importers.md.
This file is the durable extract.
