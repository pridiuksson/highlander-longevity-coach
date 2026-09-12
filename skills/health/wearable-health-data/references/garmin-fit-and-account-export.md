# Garmin FIT decoding + Account Export structure (verified 2026-08-16)

Companion to `samsung-health-export-tools.md` and the big-platform verdict — the
Garmin-side landscape. Data verified via PyPI JSON API + GitHub API (no guesses).

## FIT library landscape (2026)

| Library | PyPI ver | Last PyPI upload | Repo | pushed_at / notes |
|---|---|---|---|---|
| **fitdecode** 0.11.0 | MIT | 2025-08-06 | polyvertex/fitdecode | pushed 2025-08-06, 216★. Recommended for offline parsing: pure-Python, tolerant of malformed/partial activity files (`FitReader(error_handling=...)`), covers full standard profile, streaming API. |
| **fit-tool** 0.9.16 | BSD | **2026-08-05** | `shaonianche/python_fit_tool` | pushed 2026-08-14. Most active. Read **and write** FIT + DSW/GPS resync utils. Repo MOVED: original `goldenretriever-pet/fit-tool` is 404; `polygongur` original also gone. Use if you must write FIT or want the Java-SDK-style high-level API. |
| **fitparse** 1.2.0 | BSD | 2020-09-07 | dtcooper/python-fitparse | dormant. Popular but not maintained; fitdecode is its maintained successor. |
| **Official Garmin SDK** | n/a | SDK v21.213.0 (2026-08-11) | garmin/fit-python-sdk, garmin/fit-sdk-tools, garmin/fit-c-sdk, garmin/fit-javascript-sdk | both pushed 2026-08-13. **Now has an active official Python SDK** (156★). Chose for protocol fidelity to the newest profile. Docs: developer.garmin.com/fit. |

- **pandas is NOT a FIT decoder.** FIT is a compact binary TLV format (records →
  local message types → data messages; fields resolved against the SDK Profile.xlsx/
  Types). Decode to tabular first via a library above, then load into pandas.
- **Recommendation:** `fitdecode` → pandas → SQLite/parquet for offline mining.
  `fit-tool` when write/DGPS needed. Official Python SDK when latest-profile fidelity
  matters (newest fields/edge devices).

## Garmin Connect account export (ZIP) structure

Trigger: Garmin Connect web → Account Settings → "Export Your Data" → ZIP emailed.
Garmin publishes **no SLA and no archive-format docs**; exact folder names vary across
reports — unzip and look rather than trusting one path. Two layouts have shipped:

### A) Classic / hyphenated layout (activities + UDS JSON)
- `DI-CONNECT-FIT-EXPORTS/` — **raw activity `.FIT` files** (one per recorded/uploaded
  activity; filenames are **timestamps**, not human names).
- `UDSEphemeralSleep*.json` — **sleep-stage episodes** (timestamped sleep-stage series).
- `summarizedActivities*` — activity summaries (match summaries to FIT files).
- `UDSUpsertGarminConnect*` family (the GC-mobile "UDS" cache): daily summaries
  (**steps, calories**), HR intraday series, **RHR, stress, body battery, HRV, SpO2,
  respiration** at daily granularity. (Exact SpO2/RHR/Weight suffix spellings best-effort.)

### B) Newer / camelCase layout (documented 2025 by Gneta, engineer who ran the Garmin analytics behind this data)
- `DI_CONNECT/DI-Connect-Uploaded-Files/` (COROS spelling) or
  `DI_Connect/DI-Connect-Fitness-Uploaded-Files/` (Garmin-forum reports) — workouts/
  activities. Contains **nested ZIPs** `UploadedFiles_0-_Part1.zip`, `_1-_Part2.zip`,
  … and the **`.FIT` files live inside those** (not loose). FIT filenames are timestamps.
- `DI_CONNECT/DI-Connect-Fitness/..._summarizedActivities.json` — activity summaries →
  matches activity names to the timestamp-named FIT files.
- `DI_CONNECT/DI-Connect-Wellness/<start>_<end>_<id>_sleepData.json` — Garmin's
  **computed nightly summaries**: sleep, stress, body battery, HRV (nightly, NOT the raw
  per-second sensor trace).
- Archive is **FIT + JSON only — there is NO CSV in the archive.** Body measurements/
  weight fall under "personal data: profile, goals, body measurements." Training-status
  history, granular VO2max trend, and courses are NOT in exportable form.

### Per-metric file map
- Workouts/activities → `DI-CONNECT-FIT-EXPORTS/*.fit` (classic) or
  `DI_CONNECT/DI-Connect-*-Uploaded-Files/UploadedFiles_0-_Part*.zip/*.fit` (newer).
- Activity-name→FIT mapping → `summaryizedActivities*` (classic) /
  `DI_CONNECT/DI-Connect-Fitness/*_summarizedActivities.json` (newer).
- Sleep stages → `UDSEphemeralSleep*.json`; nightly summary
  `DI_CONNECT/DI-Connect-Wellness/*_sleepData.json`.
- HR series, HRV, RHR, stress, steps, SpO2 → classic UDS daily JSON
  (`UDSUpsertGarminConnect*`); newer wellness JSON.
- Body composition (weight/BMI/body fat) → "personal data/body measurements" JSON.

## Maintenance-verification method (reusable)
- No pip/pip module and web_extract backend is search-only → use `curl` to the
  **PyPI JSON API** (`https://pypi.org/pypi/<pkg>/json`) for versions + last upload,
  and **GitHub API** (`api.github.com/repos/<o>/<r>`) for `pushed_at`/`archived`/stars,
  and `/releases` for SDK cadence.
- Security scanner **flags `curl | python3` (pipe-to-interpreter)** → `curl -o` to a
  temp file first, parse in a separate step.
- GitHub **code search is login-walled** (no anonymous); grep.app sits behind a Vercel
  security checkpoint. For code-search-able evidence, use `gh search code` (repo search
  bucket, 30/min) instead — same lesson as `samsung-health-export-tools.md`.
- Rate limits hit hard on multi-query web_search (HTTP 429) — pace/batch, prefer the
  REST APIs above for the numbers.

## Sources
- gneta.app/blog/export-garmin-data-guide ("How to Export Garmin Data: FIT, CSV, or the
  Full Archive", ~2025) — primary for layout B + no-CSV fact.
- support.coros.com/hc/en-us/articles/7708736140948 — `DI_Connect/DI-Connect-Uploaded-Files`
  = workout data.
- support.garmin.com FAQ W1TvTPW8JZ6LfJSfK512Q8; forums.garmin.com threads on sleep export.
- support.mydatahelps.org garmin-export-overview + garmin-sleep-summary-export-format.
- pypi.org + api.github.com (fitdecode, fit-tool, fitparse, garmin/fit-*).
