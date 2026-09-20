# Samsung exercise_type SDK codes — authoritative source & verification notes

## Core rule
Codes are **public Samsung SDK constants** (developer.samsung.com `EXERCISE_TYPE`
page, 97-entry table), NOT per-account values. The *code→label* is fixed; only the
*activity-mapped-under-a-code* is account-specific for this user.

## Verified codes relevant to this user's data (SDK-confirmed 2026-08-16)
- 15005 = "Treadmill, combination of jogging and walking"
- 10007 = "Circuit training, moderate effort"
- 10006 = sit-ups, 10008 = mountain climbers (calisthenics block)
- 15002 = "Weight machine" (user overlay: gym-strength session)
- 7003 = "Martial arts, moderate pace (Judo, Jujitsu, Karate, Taekwondo)" (user overlay: combat-cardio group class)
- 11007 = "Cycling" (user overlay: with-distance=regular bike; no-distance + 2026 Stockholm = e-bike commute)
- 9002 = "Yoga" (user overlay: Bikram hot yoga)
- 1001 = "Walking" (user overlay: auto-walk)
- 1002 = "Running"

A `user overlay:` entry is the account-specific half of the mapping — the activity YOUR
export files under that code. The session count, mean duration and mean HR that verified
an overlay belong to the dataset it was verified against, so re-derive yours (count
sessions per code, compare their durations and mean HR) instead of copying a row's stats.

## Manual vs auto provenance (raw `source_type` column, NOT in sqlite — parser drops it)
Read from the raw `com.samsung.health.exercise.*.csv` `source_type` field:
- 4 = auto-detected (6,767/6,785 walks; 282 bike) — device started on its own
- 1 = manual start (all 280 gym, all 6×15005, 112 runs, 38 bike) — user pressed the button
- 2 = coaching-program-driven (8×10007 Apr-2025 abs week — `program_schedule` CSV proves
  enrollment Apr 15, sessions Apr 16–20)
- 7 = 17 walks, undetermined

## Discriminating auto vs manual empirically
- The sqlite `workout` table has NO auto/manual flag. Use the raw CSV `source_type` column
  (parse-sidecar), not the DB.
- A coaching-program week cross-checks via `exercise.program_schedule` / `exercise.program`
  CSVs (enrollment time, per-day sessions, `program_id`).

## Reliable query gotcha
Samsung export CSVs have TWO header rows (row0 format marker, row1 column names) and
column names may be bare OR `com.samsung.health.<type>.`-prefixed WITHIN THE SAME FILE.
Always read `rdr.fieldnames` first; the prefixed key is usually the populated one.
Matching `datauuid` between sqlite and the export exercise CSV is unreliable — match on
`start_time` date-prefix instead; several rows share-per-type per date.
