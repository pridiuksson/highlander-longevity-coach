# Withings Integration Landscape + Export Format (verified 2026-09-01)

GitHub forensics on Withings integration options for the headless Linux
SQLite-pipeline + MCP setup. All repo metadata via `gh api repos/{owner}/{repo}`
(stars, license.spdx_id, pushed_at — not search snippets). Read this BEFORE
re-searching GitHub for Withings tooling.

## Per-repo verdicts (sorted by fit for headless Linux/SQLite/MCP)

| Repo | Stars | License | Last push | Mechanism | Verdict |
|---|---|---|---|---|---|
| partymola/withings-mcp | 0 | GPL-3.0 | 2026-08-31 | Official API → **local SQLite cache**, incremental sync, auto token refresh | Best architecture match (SQLite + MCP), but brand-new, 0★, unproven |
| davidmosiah/withings-mcp | 4 | MIT | 2026-08-29 | Official API, local-first MCP; handles Withings **signed-token OAuth** locally | Strong fit: npm `withings-mcp-unofficial`, stdio + loopback HTTP, documented headless recipe (auth on another machine, copy `~/.withings-mcp/tokens.json` chmod 600) |
| quantcli/withings-export-cli | 0 | MIT | 2026-07-30 | Official API, Go static binary → markdown/JSON/CSV | Good lightweight one-shot ingest into SQLite pipelines; no MCP |
| akutishevsky/withings-mcp | 39 | MIT | 2026-08-30 | Official API MCP; primary UX is **hosted** `withings-mcp.com/mcp` for Claude Desktop | Weak fit headless: self-host needs public HTTPS callback (tunnel) |
| jaroslawhartman/withings-sync | 688 | MIT | 2026-04-22 | Official API CLI → Garmin Connect / TrainerRoad / raw JSON | Niche: weight/measurements only, Garmin-push focused. 2026 breaking change: garth lib replaced, full re-login |
| dbsqp/withings-influxdb2 | 5 | MIT | 2026-02-16 | Official API Docker → InfluxDBv2, hourly cron | Poor fit: Influx-coupled, not SQLite; clunky 30-s auth-code INIT dance |

Note: jaroslawhartman's 688★ is ecosystem fame for the Garmin push, not data
ingestion quality. Stars ≠ fit (same lesson as the Samsung survey).

## Withings API auth pattern (common to all six)

- All use the official OAuth2 API (developer.withings.com / wbsapi). None parse
  the export ZIP — every one is a live-API client.
- User must register their own OAuth app: client id + secret + callback URL.
- Access tokens live ~3h, refresh tokens ~1y (partymola's docs), authorization
  codes expire in ~30s–minutes → the browser-approve step is the fragile part
  on headless boxes. Two working patterns: (a) auth on a desktop, copy the
  token file to the server (davidmosiah); (b) HTTPS callback via
  redirectmeto.com bounce to a localhost listener (quantcli).
- Scopes: `user.metrics` (body/heart) + `user.activity` (activity/sleep/workouts).

## Data coverage highlights

- Broadest: akutishevsky (HRV RMSSD/SDNN, intraday activity, ECG waveform,
  stethoscope if BPM Core).
- partymola: 17 body-comp metrics, minute-level sleep phases (live, ≤7d/req),
  ECG/AFib, trends tool, `withings-mcp doctor` CLI.
- davidmosiah: body/activity/workouts/sleep summary+detail/heart; date-filter
  semantics differ per Withings action (epoch `startdate` vs civil
  `startdateymd`) — handled server-side.
- quantcli: measurements/sleep/activity/workouts → CSV for pipelines.

## Export ZIP format ("Export All Health Data" / "Download my data")

- Delivery: request in app/account.withings.com → email link → **ZIP of CSVs**,
  one per category (community post lists `weight.csv`, `activity.csv`,
  `sleep.csv` "e.g." — file names UNVERIFIED).
- Official field lists (support.withings.com article 360001391287, retrieved
  via search snippets — page itself is JS-gated):
  - Activity: date, steps, distance, elevation, active calories
  - Blood Pressure: HR, systolic, diastolic, comments
  - Weight: weight, fat mass, bone mass, muscle mass, hydration, comments
  - Sleep: from/to, light, deep, REM, awake, wake-up
  - Body Temperature: date, temperature, comments
- **Verified exact CSV schema is the IMPORT format, not the export**
  (limitedmage/fitbit-to-withings-weight-converter `csv-converter.ts`, read
  from source): Withings "Import my data" (Weight section) accepts
  `Date,"Weight (lb)","Fat mass (lb)"`, datetime `YYYY-MM-DD hh:mm:ss`,
  ≤250 rows per file.
- jimliddle/healthtracker imports Withings CSVs via fuzzy header matching
  (`date`, `weight`, `heart rate`/`pulse`, `systolic`, `diastolic`) — confirms
  column keywords, not exact export names; its README's `raw_tracker_measures.csv`
  is hedged "or similar".
- **Export column names remain unverified until a real export ZIP is opened.**
  HRV/HR/SpO₂ presence in the export: unverified.

## Re-verification recipe

`gh api repos/{owner}/{repo} --jq '{stars:.stargazers_count,license:.license.spdx_id,pushed:.pushed_at}'`
per repo (core bucket, fine to loop); READMEs via
`gh api repos/O/R/readme -H "Accept: application/vnd.github.raw" | head -c 4500`.
Landscape moves: at least three of these six repos were touched within days of
2026-09-01 — re-check `pushed_at` before any adoption decision.
