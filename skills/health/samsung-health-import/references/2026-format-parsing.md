# Samsung Health 2026 Export Format — Parsing Reference

Condensed from the verified pipeline built 2026-08-15 (`health.health_dir/samsung-data/`, adversarially audited — probes in `audit-2026-08-15/`). This is the "how the data actually looks" file; the SKILL.md carries the procedure.

## Zip layout

```
Samsung Health/samsunghealth_<user>_<YYYYMMDDHHMMSS>/     <- ts changes per export; DISCOVER, never hardcode
  com.samsung.health.<type>.<ts>.csv                       <- 63 CSVs
  jsons/com.samsung.health.hrv/<x>/<uuid>.binning_data.json <- HRV interval arrays
  jsons/com.samsung.health.oxygen_saturation.raw/...        <- sensor-channel floats (NOT %)
  jsons/com.samsung.shealth.stress/<tag>/...                <- misc blobs
  34-workout_list*.blob_value.json                          <- exercise type code list
```

CSV shape (all files): row0 = `com.samsung.health.<type>,7000107,<ver>` format header; row1 = column names; data from row2. Column names may be bare OR `com.samsung.health.<type>.`-prefixed — sometimes BOTH styles inside one file (sleep.csv: bare metrics, prefixed times/ids). Never assume; read row1 per file.

## Units (the trap table)

| Field | Unit |
|---|---|
| exercise.duration | MILLISECONDS |
| sleep total_sleep_time / stage durations in sleep_combined | MINUTES (in sleep_stage CSV: computed from timestamps) |
| weight table durations n/a; goal_bed_time etc. | MILLISECONDS |
| distance | METERS |
| HR, SpO2 %, thresholds (at/ant/max) | plain values |
| hrv binning start_time/end_time | MS EPOCH (UTC) |
| HRV sdnn/rmssd | ms |

## Timestamps

- CSV time strings are **TRUE UTC naives** (`YYYY-MM-DD HH:MM:SS.mmm`) + separate `time_offset` col (`UTC+0300`) holding the LOCAL offset. Conversion (epoch-proven 2026-08-16 — the pre-fix parser inverted this): `utc = string as-is`; `local = string + offset`. Keep BOTH. See `timestamp-timezone-truth.md` for the sidecar-epoch proof.
- Dual-timezone reality (audited; corrected 2026-08-15): **Vilnius/EET offsets (+2/+3) until the 2025-09-08 move, Stockholm/CET (+1/+2) after** — an earlier "Cyprus" attribution was wrong (offsets numerically identical, which is why conversion math reconciled either way; only lived-clock LABELING was affected). ts_utc is uniformly correct; ts_local mixes zones → night-key grouping only: `substr(datetime(substr(start_local,1,19), '-18 hours'),1,10)`. For lived-clock display: EET before 2025-09-08, CET after.
- ~650 rows (0.9%) sit on DST boundaries where hour-granularity offsets misclassify by 1h — advisory noise, ignore.
- 19 rows have delta 0 (export artifacts, e.g. 2024-11-22 cluster) — leave them; they don't corrupt aggregates.
- Placeholder rows exist (HRV had one at 1970-01-01) — skip timestamps <2020 at parse time.

## Per-series notes

- **tracker.heart_rate**: HOURLY bins (~20-26/day), each with heart_rate (avg), min, max, start/end. Covers Apr 2021→export end only partially older. NOT 10-min.
- **sleep** (2,110 rows): one row per session FRAGMENT (watch + phone each write). sleep_combined (234 rows) = night-level scores + explicit per-stage totals (total_rem_duration, total_light_duration, sleep_duration — MINUTES). Use combined as ground truth for validation, sessions for spans.
- **sleep_stage** (92k): codes 40001=awake 40002=light 40003=DEEP 40004=REM — VALIDATED by correlation vs combined explicit totals (71 nights: light r=+.90, REM r=+0.99) AND independently by population-norm analysis (auditor). Beware: shares alone (9/55/13/23%) are plausible under the WRONG mapping too.
- **exercise** (7,679): per-session metrics incl mean/max/min HR, vo2_max (runs only, 101 rows), calorie, distance, cadence. title column is EMPTY; type codes from workout_list blob, identity TESTIMONY-CORRELATED 2026-08-15 (1001 auto-walk, 1002 run, 11007 cycling-if-distance / e-bike-commute-if-no-distance-Stockholm, 15002 gym strength, 9002 hot Bikram yoga, 0 = uncatalogued (EXCLUDE from type analyses, n=56). Full map + evidence: SKILL.md.
- **exercise.hr_zone / max_heart_rate**: at/ant/max_hr per date — Samsung revises continuously (DB-verified full ladder: AT, AnT and max each stepped in sequence, 2024-03→2026-06); the 2025-12-24 revision was a routine ~monthly ratchet step (Sep-Dec 2025: ratcheted ~monthly; Dec 24 overdue at 53d), not a one-time event. Never assume fixed zones; read per-date.
- **sleep_stage / sleep / sleep_combined carry per-row `create_sh_ver` + `pkg_name` columns** (Samsung Health app-version stamps, DROPPED by our sqlite parser as of 2026-08-15): first-record date per version = install proxy; 29 dated transitions 2021-2026 (e.g. 63051050=6.30.5.105 first seen 2025-09-25). Use for software-vs-physiology arbitration; TODO: capture in parser (parked follow-up, run-005 Addendum 3).
- **hrv**: hourly windows, values in binning JSONs `[{"start_time": <ms>, "sdnn": x, "rmssd": y}, ...]` — resolve JSON path by BASENAME against a set of all zip entries (never path-join; subdirs vary). Watch 7 records continuously (day+night).
- **weight**: full BIA body composition (weight, body_fat_mass, skeletal_muscle_mass, muscle_mass, fat_free_mass, bmr). Reproduces known profile values (<YOUR_WEIGHT_KG> / <YOUR_SKELETAL_MUSCLE_KG> skeletal) — the strongest parse validation available.
- **tracker.oxygen_saturation**: per-session spo2/max/min/heart_rate/coverage_rate. Ignore the `.raw.` file.
- **respiratory_rate + skin_temperature (INGESTED 2026-08-29, parse_samsung_rr_skin.py)**: nightly windows Oct 2024→present, 773 rows each, 670/670 nights paired. RR decode: `average` = duration-weighted mean of NONZERO 60s bins (EXACT gate); lower/upper_limit = per-user personal band; is_outlier=1 ⟺ outside band (proven); ~1.1% bins trail 1-32min past session end (wake-cut tail, NOT tz). Skin decode: temperature == stat_m1; sd = sqrt(stat_m2 − stat_m1²); baseline DEVICE-computed (770/773) → deviation = temp − baseline; |dev|>5°C = device-off-skin nights (exclude from physiology). Bin JSON keys `mean/min/max`. See samsung-data/RR_SKIN_DECODE.md.

## Validation methodology that worked (ordered by strength)

1. Reproduce KNOWN values (profile: weight, skeletal muscle) — catches field/unit errors.
2. Correlate against the source's OWN explicit aggregates (stage sums vs sleep_combined totals, per NIGHT-KEY) — catches semantic swaps that plausibility review cannot.
3. Cross-table containment (workout HR band vs overlapping HR bins; workouts ≥25min — hourly bins dilute short ones).
4. Unit gates: median duration/wall-clock ratio (ms/s error → 0.001), hard range bounds, distance meters-scale.
5. Negative controls: corrupt the data (inflate 20%) and prove the gate FAILS — a gate that can't fail is theater.
6. External auditor claims → reconcile against data before acting (the "80% tz mismatch" was the relocation, not a bug).

## Residuals / open items

- RMSSD↔sleep-duration correlation ≈ 0 (609 nights) — expected weak-positive absent; don't build sleep advice on that pairing.
- VO2max series contradicts RMSSD+RHR trends — resolved as device re-estimation (threshold-ladder, 2026-08-15); stays quarantined low-confidence for advice.
- 56 type-0 workouts; stage-level splits remain consumer-grade (trend-indicative only).
- MCP server (samsung-health-mcp-unofficial@0.7.3) still can't parse 2026 format for HR-bins/sleep/workouts — our sqlite parser IS the gap fill; optional upstream PR parked.
