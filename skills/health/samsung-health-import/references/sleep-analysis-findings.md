# Sleep Analysis — Findings & Techniques (2026-08-15, July-3 export; corrected same-day)

## Measurement truths (hard-won, verified)

- **Tracked wake (session end) ≠ get-out-of-bed time.** The watch ends tracking at *detected* wake; the user stays in bed afterward. Verified: tracked-wake showed 04:30–05:30 even during years the user knows they rose at 8–9am. NEVER interpret `MAX(end_utc)` as rise time.
- **Physiological wake proxy: morning HR-rise hour** — the first hour in 03:00–10:00 where HR exceeds the night minimum by the script's fixed margin (`sleep_era_analysis.py`: `base + 12`), computed from `heart_rate` bins. This reproduced the user's known wake-time history; tracked-wake did not.
- **`ts_local` mixes timezones — the LIVED-CLOCK rule (corrected 2026-08-15):** the user lived in **Vilnius, Lithuania (EET, UTC+2/+3) until 2025-09-08**, then Stockholm (CET, UTC+1/+2). An earlier "Cyprus" attribution was wrong (identical offsets, which is why tz math reconciled either way). ALWAYS analyze on `ts_utc`; for lived-clock display use EET before 2025-09-08, CET after. Labeling Vilnius years in Stockholm clock shifts everything −1h and ERASES exactly the wake-time change the user remembers.
- **Night-key (standardized on LOCAL, matching SKILL/parsing/patterns docs)**: `substr(datetime(substr(start_local,1,19), '-18 hours'),1,10)` on start_local (a start_utc−18h variant diverges for 17:00-19:59 local starts and ~650 DST rows — do not mix). Never raw calendar-date grouping on ts_local.
- **Era × season, not era alone**: seasonal photoperiod cycling dominates wake time and persists across cities and climates (Vilnius winter 7.33/summer 6.17; Stockholm winter 7.10/summer 5.33 — lived clock).

## Verified findings (this user, 2021-08 → 2026-07)

1. **The wake-time switch is real but gradual — and it happened in Vilnius, not at the move.** In lived clock, the "8–9am rising" memory is CONFIRMED (Vilnius winters 2021–23: physiological rise 07:40–07:54 → out of bed ~08:00+). Winter rise then drifted steadily earlier, reaching ~6.9 by winter 2024/25 — the 6:30-era began before relocation. First Stockholm winter (7.0–7.3) ticked slightly LATER than the last Vilnius winter; the move did not push earlier. Seasonal cycling continued across both cities.
2. **Midwinter alarm-vs-body gap ~30–60 min** (Stockholm winter rise 7:00–7:29 vs 6:30–6:40 alarm) — revised down from an initial ~1h claim made before the lived-clock correction.
3. **Deep sleep 3.5× multi-year arc** (winter-vs-winter, same-season): 2021-12: 18 min → 2025/26: 60–67 min. REM rose to ~115 min. Awake-in-bed halved (to ~35 min). Efficiency rose to ~93.4%. Sleep HR fell by a few bpm. Monotonic across five winters.
4. **The architecture improvement is PORTABLE — it's the person, not the environment.** Deep/REM/efficiency climbed smoothly straight through the Vilnius→Stockholm move with zero step at 2025-09-08. A continental→59°N-maritime climate change (a major environmental variable in sleep research) perturbed nothing. Whatever drove it (training, recovery habits) traveled with him. Coincides with the fitness arc (RMSSD and RHR both moved in step — values withheld) — two independent sensor systems, one direction.
5. **Duration never moved** (~6.7–7.5h plateau, all eras). Better sleep, not more sleep. ~7h at 91%+ efficiency reads as capacity, not deprivation — do not prescribe sleep-extension without new evidence.

## Techniques

- **Same-season comparison is mandatory** for any "did X change my sleep" question: photoperiod dominates wake time and stage timing. Compare Dec-vs-Dec, never adjacent months.
- **Lived-clock conversion is mandatory for wake/bedtime claims**: verify which city the user lived in for the period (ask if unknown — the data cannot distinguish EET sources), then convert per era. A wrong era label silently rewrites wake-time history by an hour.
- **Era-breakpoint detection via rolling-mean drop FAILS here**: the seasonal cycle dominates and manufactures false breakpoints every spring (naively flagged "2026-04"). Use winter-vs-winter tables instead.
- **Location facts are analysis-critical**: when the user corrects a biographical fact (where they lived, when they moved), re-run era analyses that assumed the old fact before accepting prior conclusions — one label flipped two findings this session.
- **Monthly table shape that works**: rise-hour mean + n, duration, deep/REM/light/awake min per night, efficiency, sleep-window mean HR — one row per month, five years visible at a glance (see scripts/sleep_era_analysis.py).
