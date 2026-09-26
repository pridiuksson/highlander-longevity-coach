---
name: apple-health-import
description: "Apple Health export ingestion: export.xml or zip -> $HERMES_HOME/data/apple_health.db, gated, memory-safe streaming."
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
    tags: [apple, health, data-import, xml, sqlite, wearables]
    related_skills: [garmin-import, samsung-health-import, wearable-health-data, proactive-coach]
---

# Apple Health Import

> **Config.** This skill reads its paths from `config.yaml`; the resolved values
> arrive in the `[Skill config]` block injected when this skill loads. In the
> commands below `$HEALTH_DIR` = `health.health_dir`.
> The `$VARS` above are shorthands for the keys, not environment variables — Hermes injects the
> values into the message, so substitute the resolved path. Never hardcode one: a clone can
> live anywhere, and `~/health` is only a default.

## When to Use

- The user provides an Apple Health export zip (`export.zip` or `Health_data_from_Apple_Watch_.zip`)
- Rebuilding or re-importing the Apple Health SQLite pipeline
- Trend analysis of resting heart rate (RHR), heart rate variability (HRV SDNN), VO2 max, sleep architecture, and workouts
- Longitudinal health tracking for Apple Watch users

Companion to `garmin-import` and `samsung-health-import` (same conventions, separate DB, normalized at query time).

## Architecture

```
Apple Health export (zip or XML) → $HEALTH_DIR/apple-exports/export.zip
  → scripts/parse_apple_health.py (streaming iterparse, root-clearing, stdlib)
  → $HERMES_HOME/data/apple_health.db
  → scripts/test_apple_health_gates.py (ALL must pass)
```

- Parser path: `${HERMES_SKILL_DIR}/scripts/parse_apple_health.py`
- Gate validator: `${HERMES_SKILL_DIR}/scripts/test_apple_health_gates.py`
- Specification reference: [references/apple-health-data-spec.md](references/apple-health-data-spec.md)
- Export path: `$HEALTH_DIR/apple-exports/` (gitignored)
- Database: `$HERMES_HOME/data/apple_health.db` (gitignored)

## Rebuild Procedure

1. Confirm export zip or uncompressed `export.xml` is in `$HEALTH_DIR/apple-exports/`.
2. Run the streaming parser (can parse directly from `.zip` without unpacking to disk):
   ```bash
   python3 ${HERMES_SKILL_DIR}/scripts/parse_apple_health.py \
     --export "$HEALTH_DIR/apple-exports/export.zip" \
     --db "$HERMES_HOME/data/apple_health.db" \
     --rebuild
   ```
3. Run the verification gates — ALL must pass before coaching from the data:
   ```bash
   python3 ${HERMES_SKILL_DIR}/scripts/test_apple_health_gates.py \
     "$HERMES_HOME/data/apple_health.db"
   ```

## Hard-Won Facts & Traps

- **Streaming iterparse is mandatory:** `export.xml` can easily exceed 2GB–5GB+. Standard DOM parsers (`xml.etree.ElementTree.parse`) will crash or exhaust memory. The parser uses `ET.iterparse` with `root.clear()` to hold RAM strictly below 100MB regardless of file size.
- **Direct Zip streaming:** The parser reads directly from `.zip` archives via `zipfile.ZipFile.open()`, saving several gigabytes of uncompressed disk space.
- **Sleep 18:00 night-key:** Sleep sessions frequently cross midnight. Grouping by raw calendar date creates false fragments. The night key `(start - 18h).date()` reliably anchors all sleep fragments between 18:00 and 17:59 to a single night.
- **Asleep vs InBed / Awake:** Only `HKCategoryValueSleepAnalysisAsleep*` records are counted towards total sleep time. `InBed` and `Awake` records are strictly excluded from sleep duration totals.
- **Nested Workout Statistics:** In Apple Health, workout energy (`kcal`), distance (`km`), and heart rate metrics are nested inside `<WorkoutStatistics>` child elements rather than attributes on `<Workout>`.
- **Datetime offset hazards:** Apple Health timestamps carry explicit timezone offsets (`+0200`). Never compare offset-aware datetimes directly with naive timestamps.
- **Privacy & Leak Gate:** Never hardcode personal user names or device serials in parsing scripts. Real exports stay in `$HEALTH_DIR/apple-exports/` (outside git).
