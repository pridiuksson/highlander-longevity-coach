---
name: garmin-import
description: "Garmin Health data import: account-export zip → $HERMES_HOME/data/garmin.db, gated, normalized beside Samsung."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    config:
      - key: health.health_dir
        description: "Root of your health data: device exports, SQLite DB, verified-data docs"
        default: "~/health"
        prompt: "Root of your health data: device exports, SQLite DB, verified-data docs"
    tags: [garmin, health, data-import, fit, sqlite, wearables]
    related_skills: [samsung-health-import, workspace-hygiene]
---

# Garmin Health Import

> **Config.** This skill reads its paths from `config.yaml`; the resolved values
> arrive in the `[Skill config]` block injected when this skill loads. In the
> commands below `$HEALTH_DIR` = `health.health_dir`.
> The `$VARS` above are shorthands for the keys, not environment variables — Hermes injects the
> values into the message, so substitute the resolved path. Never hardcode one: a clone can
> live anywhere, and `~/health` is only a default.

## When to Use

- the user provides a Garmin "Export Your Data" account-export zip (2016-2021 era)
- Rebuilding / re-importing the Garmin sqlite pipeline
- Any cross-source analysis that needs both Garmin (2016-2021) and Samsung (2021-2027) data together
- Extending a trend series (VO2max, RHR, workouts, sleep) back before the Galaxy Watch

Companion to `samsung-health-import` (same conventions, separate DB, normalized at query time). Historical leg only — Garmin recent data would need a live-API path (not built; GarminDB/open-wearables are GPL/live-API-only references).

## Architecture

```
Garmin "Export Your Data" zip → garmin-exports/garmin_connect_export.zip
  → parse_garmin_export.py  (JSON legs: workouts, sleep, daily, vo2max; stdlib)
  → parse_garmin_fit.py     (FIT legs: fit_session ground truth, rhr_snapshot; .venv/fitdecode)
  → $HERMES_HOME/data/garmin.db  ← gates in test_garmin_gates.py (ALL must pass)
  → queries.py  (cross-source: ATTACH $HERMES_HOME/data/health.db read-only; era|overlap|summary|vo2)
```

- Parser paths: `health.health_dir/garmin-data/` (sibling of `samsung-data/`).
- Zip: `health.health_dir/garmin-exports/garmin_connect_export.zip` (gitignored).
- FIT cache: `health.health_dir/garmin-exports/fit-cache/` — extracted inner `UploadedFiles_*.zip` (~10.5k `.fit`); gitignored.
- venv: `garmin-data/.venv` (`uv venv` + `uv pip install fitdecode`); gitignored. fitdecode 0.11.0 pinned.
- Runbook (confidence tiers, gaps, unit correction, era facts): `health.health_dir/garmin-verified-data.md` — read before first advice.
- Plan + research: `$HERMES_HOME/plans/2026-08-16-garmin-import.md`, `Knowledge/Research/Tech/garmin-data-import.md`.

## Rebuild procedure

1. Confirm the zip is in `garmin-exports/` matching `garmin_connect_export.zip`.
2. `python3 parse_garmin_export.py` (rebuilds workout/sleep_night/daily_summary/vo2max/import_meta).
3. Extract inner zip to fit-cache if missing: see scripts/extract_fit_cache.py.
4. `garmin-data/.venv/bin/python parse_garmin_fit.py` (appends fit_session/rhr_snapshot/fit_progress; checkpointed, re-runnable).
5. `python3 test_garmin_gates.py` — ALL must pass. Then `--negative-control` once after any parser change.
6. Cross-source: `python3 queries.py summary`.

## Hard-won facts (this export, 2026-08-16)

- **Era detection:** derive the export's date range from its own first and last rows — never assume it, and expect a handover to a second device/source with a short overlap. Record the range and the row counts (workouts, sleep nights, daily rows, VO2max samples, FIT files) for THIS instance in the user's runbook; they are instance-specific and must not be carried across installs.
- **FIT files classify ~87% monitoring_b / ~13% activity.** Activity FITs are ground truth (1,263 fit_session = 1,263 JSON workouts, start_utc ±300s join 100%, zero ambiguous). Monitoring FITs yield `rhr_snapshot` (15,973 timestamped RHR).
- **`rule=groups` is a Garmin privacy/sharing label, NOT an aggregate.** Each of the 1,263 workouts (incl. every grouped row) matched a distinct FIT session 1:1 → they are distinct real activities, safe to count/analyse. (Earlier mis-read them as summed aggregates — false, that confusion was the unit bug below.)
- **JSON `distance` is 100× inflated, `avg_speed` is 10× inflated, `elevationGain` is 100× inflated** vs FIT (verified n=785/n=736). Parser divides distance and elevation by 100, multiplies speed by 10. **`calories` is kJ-scale and NOT a constant transform of FIT kcal** (ratio 4.154–4.208 — never divide it; parser NULLs it and backfills FIT kcal via the exact 1:1 join). NEVER re-read raw units from summarizedActivities without applying these.
- **HARD RULE (review round 2): arbitrate EVERY shared JSON↔FIT field, not just suspected ones.** Round 1 fixed distance/speed while elevation (100×) and calories (4.19×) sat uncorrected in the same rows. G11 in test_garmin_gates.py enforces this mechanically: all 8 shared fields must ratio-match FIT ±0.5%. Any new field added to the workout table must be added to G11's FIELDS list.
- **HARD RULE #2 (round 3, peer-reviewed): unit arbitration has two legs — FIT agreement AND physiological plausibility.** FIT kcal passed both: sport-wise kcal/min (gym 4.1 / hike 4.3 / walk 4.2 / swim 5.8 / ride 7.5 / run 12.2) are ACSM/Compendium-concordant, runs match the ACSM equation to ~99% at the reference speed, and cross-device runs agree. A field that matches FIT but fails physiology (or vice versa) is still unverified.
- **No REM, no continuous HR, no HRV, no SpO2, no stress series** in Garmin 2016-2021 export. **Device = Fenix 3 HR (owner-confirmed): NO REM is a hardware certainty** — this generation pre-dates Garmin's HR-based Advanced Sleep Monitoring and stages sleep from movement only; sleep deep/light are coarse classes, weaker than the Chinoy-2021-validated later Garmins. Those series stay Samsung-only.
- `rhr_snapshot` (monitoring FITs) = 15,973 timestamped RHR readings — finer than daily_summary RHR.
- **Sleep total rule**: `total_s := sleepTimeSeconds` when present, else `deep+light`. NEVER include `awake` in totals (garmin-grafana's `calculate_sleeping_seconds` omits REM and includes awake — verified bug, not ported).
- **Sleep timestamp frame (RESOLVED 2026-08-16 evening, four mechanical anchors — was misread as local-display for one morning):** `sleepStart/EndTimestampGMT` are **TRUE UTC**. Anchors: overlap-week (Garmin 21:42 vs Samsung-native 22:18, both-UTC, 36 min apart), wake testimony, workout-gap (+1.48h median, n=228; negative under local), DST seasonal shift (+1.13h winter-vs-summer wake medians — 0h if local). Local = stored + 2h winter/+3h summer (Vilnius EET/EEST era). Full chain: `health.health_dir/garmin-verified-data.md` §tz + `health.health_dir/decade-sleep/tz_dst_discriminator.py`.
- Garmin `calendarDate` = wake-date anchor ≈ Samsung night-key (start − 18h → date). **Handoff-night note (corrected 2026-08-16):** the Samsung 2021-08-25 NK night is the SAME measurement as Garmin's 2021-08-26 row (imported via Samsung Health ← Garmin Connect; identical 184/217/8 min, identical window) — there was no two-device overlap at the handoff. Any cross-era join must exclude or de-duplicate that night.
- `monitoring_hr_data` message = resting_heart_rate + current_day_resting_heart_rate snapshots (not continuous HR).

## Pitfalls

- **SQLite views cannot reference ATTACHed databases** — cross-source queries in `queries.py` are plain SQL over two connections/ATTACH, not stored views.
- Use `mode=ro&immutable=1` when ATTACHing $HERMES_HOME/data/health.db (no -wal/-shm sidecars; md5 checksum before/after import stays meaningful).
- Heredoc / redirect writes are approval-gated; use `write_file` + script files (same as samsung skill).
- `fitdecode` lives only in `.venv` — run FIT legs with `.venv/bin/python`, not bare `python3`.
- FIT pass is long (~2-4 min) and was once SIGTERM'd mid-run — the `fit_progress` checkpoint makes it resumable; don't be alarmed by a partial run, just re-run.
- Health data stays out of git: `garmin-exports/` (incl. fit-cache) + `$HERMES_HOME/data/garmin.db` + `.venv` are all gitignored.
- Garmin export layouts drift (classic `DI-CONNECT-FIT-EXPORTS` vs camelCase `DI_CONNECT`). Parser + runbook target the camelCase layout of this export; P0 inventory probe (`health.health_dir/garmin-data/garmin_inventory.py`) classifies any future zip before trusting paths.

## Cross-source analysis (Samsung + Garmin)

When answering pattern questions across the decade use `queries.py` (never hand-join raw tables from two DBs): it ATTACHes samsung read-only, exposes unified `sport_group` (run/ride/gym/hike/swim/walk/yoga/other), and aligns night-keys. Samsung `exercise_type` codes used are ONLY the testimony-validated ones (1001/1002/11007/15002/9002); unknown Samsung codes stay `type_N`/other — never guess. For cross-era volume statements use the TIER-MATCHED strict variant (Garmin minus hike+walk) — Samsung conscious has no hiking/walking counterpart, so strict is the only tier-symmetric comparison across the device handoff (verified round 3: D2-2025 conclusion holds under both, but margins change: loose 253 vs 248 [2019], strict 253 vs 195).

## scripts/

- `extract_fit_cache.py` — extract `DI_CONNECT/DI-Connect-Uploaded-Files/*.zip` from the outer zip into fit-cache.
