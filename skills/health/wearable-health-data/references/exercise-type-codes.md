# Samsung Health exercise_type codes — official SDK table

Authoritative source: **"Predefined Exercise Type | Samsung Developer"**
<https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html>
(`HealthConstants.Exercise.EXERCISE_TYPE` constants, package `com.samsung.android.sdk.healthdata`.)

Fetched 2026-08-16 via direct curl (static HTML; search backends were rate-limited); javadoc
table parsed to **97 codes, zero internal conflicts**, each priority code appearing exactly
once. Labels below are quoted verbatim from that table.

## Verified codes (seen directly in fetched table)

| Code | Official SDK label (exact quote) | Corroboration (parser code) |
|---|---|---|
| **15005** | "Treadmill, combination of jogging and walking" | lionheart L113 `15005: "running",  # treadmill` |
| **10007** | "Circuit training, moderate effort" | lionheart L61 `10007: "cross training",` |
| 1001 | "Walking" | lionheart README `1001 \| Walking` |
| 1002 | "Running" | lionheart README `1002 \| Running` |
| 11007 | "Cycling" | lionheart README `11007 \| Cycling` |
| 15002 | "Weight machine" | lionheart L110 `15002: "strength",` |
| 9002 | "Yoga" | lionheart README `9002 \| Yoga` |
| 10006 | "Sit-ups" | — |
| 10008 | "Mountain climbers" | — |
| 15001 | "Step machine" | — |
| 15003 | "Exercise bike, Moderate to vigorous effort (90-100 watts)" | — |
| 15004 | "Rowing machine" | — |
| 15006 | "Elliptical trainer, moderate effort" | — |

Useful structure: 10006 sit-ups / **10007 circuit training** / 10008 mountain climbers are
adjacent codes (calisthenics block) — short coach-driven abs/circuit sessions fit 10007.

## Source verdicts

- **AUTHORITATIVE**: developer.samsung.com EXERCISE_TYPE page (above). Consult before any
  third-party table.
- **CORROBORATES**: `lionheart/health-csv-importer-samsung` → `convert_samsung_to_health_csv.py`
  (GitHub main). Correct on every overlapping code. (Note: repo has no detectable LICENSE —
  fine to cite, not to embed in redistributed code.)
- **WRONG — do not cite**: `Devasy/samsung-health-sdk` → `samsung_health_sdk/metrics/exercise.py`.
  Conflicts with official (claims 4003=Yoga vs official 9002; 1003=Cycling vs official 11007)
  and **omits 15005 and 10007 entirely**.
- **WRONG — do not cite**: openwearables.io blog — states "1001 for running, 1002 for walking",
  **swapped** vs official table.

## Refetch recipe

```
curl -sL "https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html" -o /tmp/exercise_type.html
```
Parse: split on `<tr`, extract `<td>` cells, strip tags + HTML-unescape; pair a purely-numeric
cell with the following label cell. Sanity-check: ~97 codes, no code with two different labels.

## Interpretation layering (the part that IS account-specific)

Official label = **base layer**. What the user actually did under a code is user-specific —
testimony/data correlation overrides (see `samsung-health-import` skill, exercise type notes):
- 11007 official "Cycling" → Stockholm-era no-distance 11007 = **e-bike commutes** (user rule).
- 9002 official "Yoga" → user's classes = **Bikram hot yoga** (user-confirmed).
- 15005 official "Treadmill (jog+walk)" → fits step-based signature (cadence 86–133 spm,
  watch-estimated distance, 4–6 km/h). If a 15005 session ever carries a GPS track, that
  contradicts "treadmill" — ask the user before labeling.
- 10007 official "Circuit training" → fits short 3–8 min Samsung-coaching-program abs
  sessions (program_schedule-proven).

So: codes ARE vendor constants (transferable Samsung↔Samsung); the ACTIVITY under a code is
what needs user confirmation. Never invent codes from other vendors' schemas.
