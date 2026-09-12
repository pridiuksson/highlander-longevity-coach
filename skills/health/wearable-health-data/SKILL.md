---
name: wearable-health-data
description: "Use when importing Samsung Health/wearable data exports."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    config:
      - key: health.health_dir
        description: "Root of your health data: device exports, SQLite DB, verified-data docs"
        default: "~/health"
        prompt: "Root of your health data: device exports, SQLite DB, verified-data docs"
      - key: health.baseline_doc
        description: "Your baseline document — the single source of truth for every measured value"
        default: "~/health/baseline.md"
        prompt: "Your baseline document — the single source of truth for every measured value"
      - key: health.db
        description: "SQLite database holding the imported, normalized device data"
        default: "${HERMES_HOME}/data/health.db"
        prompt: "SQLite database holding the imported, normalized device data"
    tags: [health, quantified-self, samsung-health, wearables, data-ingestion]
---

# Wearable Health Data Ingestion

> **Config.** This skill reads its paths from `config.yaml`; the resolved values
> arrive in the `[Skill config]` block injected when this skill loads. In the
> commands below `$HEALTH_DIR` = `health.health_dir`, `$BASELINE_DOC` = `health.baseline_doc`, `$HEALTH_DB` = `health.db`.
> Never hardcode a path — a clone can live anywhere, and `~/health` is only a default.

Importing training/wellness data (HR, HRV, sleep, exercise, VO2max, steps) from
consumer wearables into storage on the Hermes Linux server (headless, no Android).

## When to Use

- **The user asks to import, parse, store, or analyze Samsung Health / Galaxy Watch
  (or other wearable) export data on the server.
- **Cross-device or decade-spanning analysis** (Garmin↔Samsung comparison,
  bedtime/duration trends, year-over-year): read
  `references/cross-device-sleep-analysis.md` FIRST — timestamp conventions
  (BOTH devices' sleep/workout fields resolved TRUE UTC, 2026-08-16 evening;
  the three-reading saga + frame-discrimination rule), imported-night
  exclusion, device stratification, matched-window comparison rules, verified
  exercise-type codes.
- The user asks which open-source tool to use for wearable health-data ingestion,
  or wants the tool landscape re-checked for new/abandoned projects.
- **Withings side of the landscape** (MCP servers, sync CLIs, export-CLI,
  the one-shot "Export All Health Data" ZIP format): read
  `references/withings-integration-landscape.md` FIRST — per-repo verdicts
  (all six repos live-API OAuth2, none parse the export ZIP), headless auth
  patterns, and the verified-import-vs-unverified-export schema distinction
  from 2026-09-01, before re-searching GitHub.
- **Pulling Withings data directly via the official Public API** (OAuth2 token
  lifetimes/rotation, measure/sleep/activity/heart/notify endpoints, pagination,
  webhook subscribe, OpenAPI spec URL): read `references/withings-public-api.md`
  FIRST (verified 2026-09-01 from developer.withings.com `llms.md` +
  `openapi.yaml`). Key traps: refresh-token ROTATION (persist the new token from
  every refresh — the old one dies in 8h), no public-client/PKCE flow
  (client_secret required → refresh must run server-side), sleep `get` capped at
  7-day windows per call, and `api-reference/` is a JS shell (use llms.md/YAML).
- **Garmin side of the same pipeline** (importer evaluation, account-export zip
  parsing, GarminDB schema reference): read
  `references/garmin-export-tools.md` BEFORE re-searching — verdicts, zip
  layout (`DI-Connect-*` tree), and GarminDB table definitions verified 2026-08-16.
- **Verifying the Garmin FIT ground-truth leg** (workout↔FIT 1:1 join, unit
  arbitration, rhr_snapshot semantics): read
  `references/garmin-fit-verification.md` — independent read-only numbers from
  $HERMES_HOME/data/garmin.db (exact-to-the-second join, n=785, 88% cross-file RHR dupes),
  for sanity-checking parser/gate claims.
- The user asks whether a bigger self-hosted platform (wger, FitTrackee, Endurain,
  GarminDB, etc.) is worth adopting instead of a custom pipeline — see
  "Big-platform verdict" below before re-surveying.
- The user shares a Samsung Health export (ZIP or `com.samsung.health.*.csv` files).
- **Hand-processing a specific workout** (rep splits, per-rep HR/speed/altitude,
  maximal-effort events, HRmax plateau checks) → read
  `references/exercise-sidecar-channels.md` FIRST — the per-workout channel-file map
  (structure-only vs data files, naming-generation trap, epoch-ms timestamps) and the
  rep-extraction recipe. Skipping it cost 6 failed probes in one session; smoothed-HR
  bout windows ≠ wall-clock windows, and per-rep GPS altitude is noise.
- **The user shares Samsung Health app SCREENSHOTS of a workout** (chart screens or
  the Swedish Träningsdetaljer details screen) to extract before the raw export
  lands → read `references/screenshot-workout-parsing.md` FIRST — dual-pass
  vision+OCR process ("ocr, vision, cross-match", user-prescribed), cross-match
  layers, pixel-tolerance limits, and the details-screen-arbitrates-chart-pixels
  rule (a chart read missed a <YOUR_RESTING_HR_BPM> max that the summary screen settled).
- **VO2max estimation work** (anchor debates, sensitivity questions, out-of-sample
  validation of the HR→VO2 line, method-family disagreement triage) → read
  `references/vo2max-estimation-lessons.md` FIRST: sensitivity-analyze a contested
  prior BEFORE debating it (HRmax 205-vs-198 was a −0.8 non-issue), validate the line
  on its most extreme fresh point (maximal rep sat at 95.3% of anchored estimate),
  convergent-evidence ranking incl. quarantined-for-cause methods (Uth at low RHR),
  formula-vs-data precedent (Tanaka off <YOUR_RESTING_HR_BPM>).
- **Researching a Samsung Health derived metric** — what it claims to measure, whether
  it's validated, official bands/thresholds, community score ranges (e.g. the AGEs
  index `com.samsung.health.advanced_glycation_endproduct`) → read
  `references/ages-index-research.md` FIRST (verified 2026-08-29) before re-searching.
- **Enrichment layer** — MapMyRun aux-merge, recovery-HR decay curves, sleep-scoring
  backfill, workout extras + per-workout HR summaries (built 2026-08-29): read
  `references/enrichment-parsers-2026-08.md` before touching those parsers/tables.
  IMPORT_PLAN.md in `samsung-data/` is the plan-of-record; runbook findings 11-12.
- **The export shows a discrete step in a derived metric** (sleep-stage counts,
  sleep score, Energy Score, max-HR, VO2max, aerobic-threshold/HR-zone estimates)
  on a known date → check the FIRMWARE/APP UPDATE TIMELINE before attributing it
  to behavior, environment, or illness. See "Firmware re-scoring checks" below.
- **Sleep-architecture pattern mining** — deep-sleep strata (>50/>90 min), day-before
  activity drivers, deep↔REM coupling, multi-year stage trends → read
  `references/sleep-architecture-analysis.md` FIRST (method v2 verified 2026-08-29:
  full-timestamp night keys, main-sleep filter, UTC durations, era-stratification
  against cohab/firmware step dates, duration-band controls, mean-vs-tail rigor).
  Every checklist item there exists because omitting it produced a wrong headline
  first — night-key attribution errors INVERT effects, and era-confounds (5/6
  "run-tail" nights pre-cohabitation) fake modality effects outright.
- **A derived metric DRIFTS or collapses gradually and you must attribute it**
  (deep/REM minutes, sleep score, HRV — 3-way: circadian/bedtime vs algorithm
  restage/re-label vs training load): read `references/metric-change-attribution.md`
  FIRST (REV A 2026-08-30 — its own worked example was partially voided by audit,
  which is why the method is trustworthy now). **Gate Zero before any ranking:**
  re-derive every load-bearing input series from raw with canonical time tooling
  and testimony-anchor it ("does this match lived experience?") — a 4-expert panel
  voted 4-0 on two fabricated series before this gate existed. Verified fingerprint
  for classifier relabel: stage-share shift INSIDE fully-staged nights (deep ↓,
  light ↑, staged total flat). The unscored-gap "smoking gun" is DEMOTED to
  hypothesis-only — it must be re-derived per-night and did not survive its only
  field test. Decisive restage test unchanged: re-import byte-diff of identical
  night-keys. Verify a lever EXISTS before protecting it (run-008's "validated
  earlier-bedtime lever" was derived from the fabricated series and died with it).

## Firmware re-scoring checks

When a dated anomaly in derived sleep/HR metrics needs arbitrating against
device-side software changes:

1. Build a dated firmware/OS timeline for the device (rollout dates per region
   wave; Samsung ships ~quarterly watch patches + a major One UI Watch OS
   update Sep–Dec). Start from
   `references/galaxy-watch-firmware-timeline.md` (Galaxy Watch 7, verified
   2026-08-15) — don't re-search history it already covers.
2. Arbitration rule: an update rolling out within ~±2 weeks of the data step
   materially strengthens the firmware-re-scoring branch; one far from every
   step weakens it. Also weigh the quarterly cadence — a step landing near a
   patch window can be coincidence.
3. Samsung never documents scoring internals (sleep stages, HRmax, VO2max) in
   changelogs. Evidence hierarchy: dated rollouts (SamMobile/SammyGuru carry
   firmware PDA codes + region waves) > feature-level announcements (Samsung
   Newsroom) > contemporaneous user reports (9to5Google indexes Reddit waves).
4. Confound: Sleep Score / Energy Score are partly computed phone/cloud-side
   (Samsung Health app + One UI phone updates). A watch-OTA-only causal story
   is incomplete — check phone-app update timing too.

## How tools get the data (server-friendliness order)

1. **Export parsers — best for deep history.** Parse the CSVs/ZIP from the vendor's
   "Download personal data" feature. Pure file processing; cron-able; no phone needed.
   Limit: data only as fresh as the user's manual export; the ONLY source for HRV,
   1 Hz sidecars, skeletal muscle mass.
2. **Health Connect bridges — best for freshness; LIVE in this pipeline (2026-08-30).**
   Continuous sync via an Android phone in the loop. the user's leg: PULL-mode (user launches
   the app's local HTTP server whenever; agent pulls over Tailscale) — user chose pull
   over push ("you'd have much better control"). Read `references/hc-webhook-pull-leg.md`.
   Working pattern worth copying: a stdlib receiver service with two-layer dedupe
   (byte-archive + identity-keyed normalized tables) makes repeated overlapping pulls
   idempotent by construction.
   **Processing the pulled data** (Hc data → queryable `$HERMES_HOME/data/health.db`):
   `hcwebhook/hc_sync.py` is the one-command operator entry (pull → crossmatch → parse),
   wrapping `pull_hc.py` / `crossmatch_hc_vs_export.py` / `parse_hc_sqlite.py` (gates H1–H6);
   `hcwebhook/hc_watchdog.py` is the staleness alert (cron hc-pull-staleness-watchdog).
   See the skill references for the mandatory cross-payload dedupe + steps
   mixed-granularity rules — skipping them double-counts data.
3. **Vendor SDKs** (Samsung Health Data SDK etc.) — on-device Android only; useless headless.
4. **Cloud scraping** — brittle; this niche is full of dead projects.

## Samsung Health export format notes

- Obtained in-app: Settings → Download personal data (arrives as ZIP).
- **VERIFIED 2026-08-15 against a real 280MB export** (full parsing reference incl. column maps, unit traps, binning-JSON layouts, dual-timezone handling: `samsung-health-import` skill → `references/2026-format-parsing.md`). Headlines: files are `com.samsung.health.<type>.<one-export-timestamp>.csv` (NOT monthly splits); every CSV has TWO header rows (row0 format header, row1 column names, data from row2); column names may be bare or `com.samsung.health.<type>.`-prefixed within the SAME file; `exercise.duration` is MILLISECONDS; HR bins are HOURLY; HRV values live in sidecar binning JSONs under `jsons/`.
- **The davidmosiah MCP server (the landscape pick) does NOT fully parse the 2026 format** — 0 workouts, 0 sleep, 217/50614 HR rows indexed. A local stdlib parser fills the gap (`health.health_dir/samsung-data/`); treat the MCP as inventory probe, sqlite as analysis source.
- **Format drift**: newer exports add `exercise.extension`, `exercise.route`, `exercise.weather` sidecar files and changed daily-calorie date formats. Parsers last touched before ~2024 may silently miss data — prefer parsers updated within a year, and verify against the newest export before trusting completeness.

## Verified tool landscape (checked 2026-08-15)

Full table with stars/push dates/licenses (all via `gh api`, no guesses):
`references/samsung-health-export-tools.md` — read this before re-searching GitHub.

Headlines:
- **davidmosiah/samsung-health-mcp** — MCP server over the CSV/ZIP export; active
  (pick for agent-native access). 9★, 13 commits/30d, sole-dev bus factor. MIT
  (verified 2026-08-15 via `gh api repos/davidmosiah/samsung-health-mcp --jq '.license.spdx_id'` → `MIT`). Author also
  runs a ~15-server "Delx Wellness" ecosystem incl. `delx-wellness-hermes` (17★), a
  Hermes-specific one-command wellness profile wiring Samsung/WHOOP/Garmin/Oura/Strava/
  Withings connectors in. MCP landscape detail:
  `references/health-mcp-server-landscape.md` (verified 2026-08-15).
- **Devasy/samsung-health-sdk** — PyPI `samsung-health-sdk`; pandas DataFrames; HRV-readiness/sleep/stress feature engine (pick as ingestion library).
- **v-2841/samsung-health-export** — zero-dep stdlib script → one self-describing JSON with per-datatype coverage manifest (pick for completeness auditing).
- **joaoruimatos/samsung-health-to-garmin** — most current on newest export-format quirks; Garmin-focused output but its Samsung parsing layer is reusable.
- Health Connect path (continuous sync, needs Android phone in loop): phone exporter
  **mcnaveen/health-connect-webhook** (145★, AGPL, alive — v1.9.17 2026-08-28; **VO2max
  confirmed in payload 2026-08-30**, the earlier "no VO2max" note was wrong) or
  **owen282000/life-dashboard-companion-app** (36★, MIT, 25 data types + HMAC signing);
  server receiver **wysie/health-connect-webhook-receiver** (stdlib Python → SQLite).
  **THIS LEG IS LIVE for the user** (2026-08-30, pull-mode over Tailscale; verified stage/
  exercise-code semantics, dedupe behavior, coverage gaps): read
  `references/hc-webhook-pull-leg.md` FIRST before any work on it.

## Big-platform verdict (checked 2026-08-15 — don't re-survey without reason)

**No mature self-hosted platform natively ingests Samsung Health.** wger (6657★),
FitTrackee (1154★), Endurain (2138★), GarminDB (3253★, CSV importers schema-locked to
MS-Health columns), jimmykane/quantified-self (221★) are all Garmin/Strava/GPX-shaped.
A custom MCP + webhook pipeline is the standard pattern, not a reinvention.
Full per-platform table + gh-CLI field quirks + 100-repo survey workflow:
`references/samsung-health-export-tools.md`.
- Multi-provider platform: **the-momentum/open-wearables** (2342★, 50 commits/30d,
  org-backed, self-hosted FastAPI+React) — unifies Garmin/Whoop/Oura/Apple Health/
  Google Health Connect/**Samsung Health** (via their Kotlin SDK
  `the-momentum/open_wearables_android_sdk`) behind one API, with a bundled MCP server
  in `mcp/` (stdio via uv: activity/sleep/workout/timeseries summaries). Only org-backed
  actively-developed multi-provider option; Samsung path requires running their Android
  companion app. Successor to their 250★ apple-health-mcp-server.
- Architecture worth forking (not adopting — 0★ personal homelab project, but 23
  commits/30d): **pricejoshua/health-connect-mcp** — Health Connect SQLite export zip →
  rclone/Drive cron → local SQLite (all 77 HC record types raw + materialized
  heart_rate_hourly) → 11 MCP tools incl. raw SQL `query_table`. The recurring-sync
  upgrade path off manual CSV drops.

## Pitfalls

- **Skills drift from pipeline truth — sweep before closing the session.** After any
  session that changes parser semantics, rebuilds a DB, or rewrites runbook numbers,
  grep every skill + reference that documents the changed behavior and fix them in the
  SAME session. Precedent (2026-08-16): the Samsung parser's tz inversion was found,
  fixed, and rebuilt in the evening — and `samsung-health-import/SKILL.md` + its
  parsing reference still taught the inverted conversion (`UTC = local − offset`)
  hours later, caught only by an explicit end-of-session sweep. Keep the installed copy and this
  repo in sync deliberately — symlinks are NOT a versioning mechanism here (a symlink carries no
  recorded revision, so drift is undetectable); re-copy and record the commit instead.
- **Timestamp timezone: ALL Samsung Health 2026-format CSV strings are TRUE UTC (epoch-proven 2026-08-16).** `start_time`/`end_time` in exercise, heart_rate, sleep session, sleep stage, sleep_data, and hr_threshold are UTC naives; `time_offset` ('UTC+0300') is the LOCAL offset. Correct conversion is `utc = string as-is`, `local = string + offset`. The parser's `to_utc()` helper assumes naive-LOCAL and SUBTRACTS offset, so it STORES the UTC value as-if-local and writes `start_utc` = UTC−offset (double-subtracted) — both columns wrong for every family. **Epoch arbiter that settled it:** sidecar jsons under `jsons/com.samsung.health.<type>/<hex>/<uuid>.{liv,binning_data,sleep_status}.json` carry absolute ms epochs — verified for ALL families (exercise `.liv` 1744865076251→04:44:36 UTC == CSV `'2025-04-17 04:44:36'`; heart_rate binning json first/last bin UTC == CSV start/end string; sleep_data `sleep_status` json epoch 1631057760000 == sleep session CSV `'2021-09-07 23:36:00'` and the sleep_stage rows span exactly the session's UTC bounds). **No family uses a different/local convention.** Prior note that "sleep appears local" was retracted — the Garmin-handoff night (healthsync app, pkg `nl.appyhapps.healthsync`, offset +0200) is the ONLY exception because it was IMPORTED from Garmin (local-display) rather than recorded by Samsung's detector; keep it excluded from native sleeps. Full proof + per-family fix + repair note: `references/timestamp-timezone-truth.md`. Correct repair: `fix_utc = current_ts_local`, `fix_local = current_ts_local + offset`. **FIX LANDED 2026-08-16 evening: parser rebuilt (`to_utc` = raw as-is; new `to_local` = raw + offset), all gates re-pass, $HERMES_HOME/data/health.db md5 638da6ad.** Scope correction 2026-08-29: that fix covered ONLY `parse_samsung_export.py` — `parse_samsung_extras.py` still carried the inverted `to_utc` and was missed by the 08-16 sweep; discovered via a DB-vs-raw min-timestamp check (body_composition ts_utc 04:38 vs raw CSV 07:38 = −3h), fixed + full rebuild same day (md5 5ffe93cc). Pre-2026-08-29 analyses touching extras tables (hrv_window, body_composition, stress, spo2) by ts_utc may need re-checking; hrv_sample epoch path was always correct. Lesson: "fix landed" claims must enumerate EVERY affected artifact, and sweeps verify per-artifact (e.g. DB min-timestamp vs raw CSV), not by trusting prior fix prose. Extras X1 gates are now self-consistent (DB counts == ingested counts; no frozen export-size numbers) and both parsers resolve CSV filenames dynamically (`resolve()`, fails loud) — export filenames carry a per-export 14-digit timestamp, never hardcode it.**
- **Garmin sleep frame: ALSO TRUE UTC (resolved 2026-08-16 evening, peer-reviewed + DST-anchor fourth line).** `sleepStart/EndTimestampGMT` meant what it said. Four independent mechanical anchors, worked protocol incl. the DST seasonal-median test and the import-copy circularity trap: `references/timestamp-frame-discrimination.md` (owned by this skill). Discriminator = the overlap week: Garmin 21:42 vs Samsung-native 22:18 both-as-UTC = 36 min apart (two algorithms, one sleeper); the intermediate "local-display" reading was CIRCULAR — it anchored Samsung-as-local to prove Garmin-as-local on the very morning the Samsung parser inversion was found, and its "interleaving proof" was a date-pairing join bug. **Frame-discrimination rule (the day's core lesson): settle timestamp conventions ONLY with mechanical anchors — epoch millis in sidecars, same-night multi-device overlap, user testimony on known wake times, downstream-impossibility tests (e.g. negative sleep→workout gaps under a hypothesis), or DST seasonal-shift medians in DST regions (winter-vs-summer string medians shift ~1h iff strings are UTC; measured +1.13h here) — never with another column whose own convention is unproven, never from field-name semantics, and never from a verbatim import-copy (a minute-identical row in a UTC column proves the IMPORTER assumed UTC, not that the source emitted it — flagged circular by peer review 2026-08-16 evening).** When a published number has already flipped twice, don't flip a third time without a NEW mechanical anchor: freeze the artifact, name the missing discriminator, resolve it (peer-review loop: hand the peer primary data + inference chain, demand it name the weakest anchor, execute its demanded mitigation, publish the negatives — e.g. RHR-in-window containment was weak at 13.2% vs 10.0% and is recorded as non-decisive). Consequence: decade bedtimes drifted later in the Garmin/Vilnius era, then back earlier in the Samsung era (REV B 2026-08-30 via `health_time.py` — the earlier reading was biased ~2.5h early by fragment starts on 223 nights; the drift conclusion SURVIVES, slightly stronger); handoff-week cross-device agreement 18 min validates the join.
- **A date-paired "interleaving" show-probe can silently pair the WRONG nights** (2026-08-16): matching sleep fragments to exercise sessions by *start* date (instead of the night the exercise belongs to) fabricated a "workout 30 min before sleep end" that never existed. When proving two series interleave, match on the *night-key* (start−18h → date) of the non-sleep series, not its raw calendar date.
- **GarminDB does NOT parse the account-export zip** (GPL-2.0, login/USB import
  only — verified by grep, zero DI_CONNECT refs). For offline Garmin export:
  arpanghosh8453/garmin-grafana (BSD-3) has the reusable zip-parsing logic but
  writes InfluxDB and skips monitoring FIT msgs; garth is DEPRECATED (repo:
  matin/garth, not mtin/martin). Full detail: `references/garmin-export-tools.md`.

- **License-less repos** (e.g. lionheart/health-csv-importer-samsung): fine for internal
  use, not for redistribution — check `license.spdx_id` before embedding in anything shared.
- **Copycat repos** duplicate popular parsers with no fork link (seen: a near-clone of
  Devasy's SDK created weeks later). Check `created_at` + `.parent` before adopting.
- **Known-dead repos** (do not re-evaluate without reason): klangenk/Samsung-Health-API,
  peje66/shealth2tcx, cjae/rn-samsung-health-data-api, AkshayMathur92/SyncHealth.
- **Staleness**: this landscape moves slowly but does move — re-verify `pushed_at` via
  `gh api repos/{owner}/{repo}` before long-term commitment. Re-run discovery with
  `gh search repos 'samsung health export' --sort updated` and
  `gh search code 'com.samsung.health.heart_rate'` (see the github skill → Repo Discovery).
- **gh search rate limit is separate and tiny**: `gh search repos` draws on a 30/min
  search bucket, NOT the 5000/hr core `gh api` bucket — batched keyword sweeps (12+
  queries) exhaust it immediately. Check `gh api rate_limit --jq .resources.search`,
  pace queries with `sleep 2`, and verify per-repo details with `gh api`/`gh repo view`
  (core bucket) which barely depletes.
- **README license badges lie**: `licenseInfo.spdxId: NONE` from `gh repo view --json`
  is the ground truth for "is there a detectable LICENSE file". Nearly every health-MCP
  repo found on 2026-08-15 (incl. Taxuspt/garmin_mcp 984★, neiltron/apple-health-mcp
  564★, and all davidmosiah servers) showed NONE despite MIT badges in READMEs.
- **Search-result noise**: multi-word `gh search repos` OR-matches loosely —
  `topic:mcp-server fitness` returned n8n, gemini-cli, awesome-mcp-servers. Vendor-name
  keyword searches (`garmin mcp`, `whoop mcp`, `strava mcp`, `withings mcp`) gave
  clean, complete result sets; lead with those.
- **Exercise-type codes: official SDK table first, user testimony on top** (updated
  2026-08-16): codes are PUBLIC Samsung SDK constants, not per-account values — the
  authoritative 97-entry table is developer.samsung.com's `EXERCISE_TYPE` page (see
  `references/exercise-type-codes.md` for the table, source verdicts, refetch recipe).
  Verified: 15005="Treadmill, combination of jogging and walking", 10007="Circuit
  training, moderate effort" (calisthenics block: 10006 sit-ups, 10008 mountain
  climbers), 15002="Weight machine", 11007="Cycling", 9002="Yoga", 1001="Walking",
  1002="Running". What IS account-specific is the activity under a code — this user's
  verified overlay (runbook rule 8): 1001=auto-walk, 1002=run, 15002=gym-strength,
  11007=bike (with-distance=regular, no-distance+2026-Stockholm=e-bike commute),
  9002=Bikram yoga; unknown code → check the SDK table, then ask the user (`references/exercise-type-code-source.md`
  holds the auto/manual provenance + two-header-row query gotcha). Never invent
  codes from another vendor's schema (a YoY comparator draft did — all wrong), and avoid
  two bad sources: Devasy/samsung-health-sdk's map conflicts with official and omits
  15005/10007; openwearables.io has 1001/1002 swapped.
- **Never compare full-year vs partial-year aggregates** (2026-08-16): full-2025
  vs 7-month-2026 totals looked flat (+2%) while the matched Jan-1..Jul-3 window
  showed the real story (conscious training +113%). Cut BOTH periods to the
  identical calendar window before any year-over-year claim.
- **Trend-in-a-mixed-population trap (2026-08-29, HRR series):** a year-over-year
  metric computed over ALL workouts can be pure workout-mix drift — the recovery-HR
  drop looked like it doubled 2022→2026 (10→<YOUR_RESTING_HR_BPM>), survived starting-HR controls,
  yet runs-only was FLAT (~<YOUR_RESTING_HR_BPM> all years): 2022-23 was e-bike commutes
  (sub-maximal), 2024-26 runs. Before calling any cross-year trend a fitness change:
  stratify by activity type AND re-run within the dominant type; check whether the
  metric is mechanically bounded by a session-intensity proxy (here: hr_start). A
  subagent checker that passes 3 confound tests can still miss the one that matters —
  run your own stratified probe before publishing the claim.
- **Era-stratify BEFORE celebrating a tail effect (2026-08-29, deep-sleep run-tail):**  "deep ≥90-min nights 3× enriched after runs" (Fisher p=0.005, survives the
  pre-registered ×8 family) still collapsed when split by a life-event boundary —
  5 of the 6 "tail" nights sat pre-cohabitation, and the post-boundary group mean
  fell below baseline (run-night deep 89.8 pre vs 46.7 post). Multiplicity
  correction is NOT the last defense: an unexamined era boundary (move-in,
  firmware wave, season, job change) can manufacture or erase a tail. For any
  claim resting on <20 events, list the events, plot them on the calendar, and
  check what fraction predates each candidate boundary.
- **Duration-band control before naming a "modality floor" (2026-08-29):** an
  e-bike-only deep-sleep "floor" (−6 min vs baseline) shrank to −2 min noise once
  nights were compared within a fixed duration band (7.0–7.5h) — the group just
  slept less overall. Before crediting a group difference to the group itself,
  re-run the comparison inside duration bands; if ordering scrambles across
  bands, the effect is duration, not modality.
- **Namespaced-uuid trap (sleep_combined, 2026-08-29):** derived/coaching tables can
  carry their OWN datauuid namespace that does NOT join to the parent table's
  datauuid (sleep_combined → sleep_session: 0/245 by uuid, 245/245 by session
  time-window ≤6h). When a join gate reports total mismatch, suspect namespace
  collision and fall back to timestamp-window joins.
- **Claim "44 scoring columns" when the raw count is 43** (2026-08-29): counting
  populated columns from a dict that still contains the join key (`datauuid`)
  inflates the number by one; the checker's fresh re-derivation caught it. Any
  "N columns" claim must come from the same filter the backfill used (join keys
  excluded), not from an ad-hoc probe.
- **Introspect house-table schemas before writing SQL** (3 failed probes in one
  session, 2026-08-29): `sleep_stage` uses `stage_code` + `duration_s`; `sleep_session`
  has NO duration column (derive `end_local − start_local`); `heart_rate` hourly bins
  carry `hr`/`min_hr`/`max_hr` (maxima in `max_hr`, `hr` is the bin mean).
  `sleep_session.sleep_latency` / `bedtime_detection_delay` are MILLISECONDS
  (540000 = 9 min — divide by 60000 before any latency claim; a "stable 5-9 min"
  latency read used this to exclude fragmentation in the Aug-2026 deep collapse).
  Memory of a schema is not the schema — `PRAGMA table_info()` first.
- **Canonical time tooling or nothing (2026-08-30, third timing incident).** All
  time-of-day statistics MUST route through `health.health_dir/health_time.py` (zoneinfo
  lived clock Vilnius→Stockholm @2025-09-08, exact DST, circular 18:00-anchored
  medians, longest-≥3h-session bedtime, `median_clock()`; regression-tested in
  `health.health_dir/test_health_time.py` — 22/22, one test class per real incident). Three
  fabricated claims in one month came from ad-hoc probe code: BC "afternoon"
  (utc-as-local), Bikram hours (utc-as-local), and a fake "4-month bedtime
  advance" (naive clock-string median + sub-3h fragments — a midnight-straddling
  week errs 90 min on realistic data; see test T2). Naive `statistics.median` on
  clock strings is BANNED; `min(session starts)` as bedtime is BANNED (evening
  fragments poisoned 223 nights ~2.5h early in the decade pipeline — REV A's
  Samsung bedtimes shifted ~1 h later under the module; trend survived,
  slightly stronger). New time-series code without a regression test is how the
  next incident gets born.
- **Sub-3h sleep sessions are fragments, NOT naps (2026-08-30, user testimony:
  "I don't do naps, like ever").** Only 23/392 sub-3h sessions in 5.5y start in
  the 12-18 nap window; 147 are evening 18-24 pre-sleep wind-down detection
  (ending 11-76 min before main-sleep onset), 116 night splits, 106 post-wake
  dozing. Never label or count them as nap behavior; Samsung's own `nap_score`
  column is set on just 12. Filter by ≥3h main-sleep; classify by start window
  if fragments matter to the question.
- **Report format for analysis close-outs (user preference, 2026-08-30):** lead
  with a plain "ballpoint" executive summary AT THE TOP — the verdicts and the
  actions, no preamble — then the detail (per-finding tables, evidence, caveats).
  When the user says "I don't understand" or "summarise into ballpoint", the
  failure is information architecture, not content: answer-first, one line per
  conclusion, each conclusion paired with its action (or "no action"). Same
  hierarchy on corrections: what your testimony broke → what was wrong → what
  changed → what it means for you.
- **Sparse sidecar streams defer to device summaries** (2026-08-29): 2021-23
  per-workout HR sidecars hold 11-59 samples (fragments), so sidecar means deviate
  from device summary means by up to <YOUR_RESTING_HR_BPM>. Density-gate (hr_n ≥ 300) any
  sidecar-vs-summary comparison; for sparse streams the summary wins. Conversely a
  recovery curve legitimately outranks a STALE summary max (proven: summary 165 vs
  curve 171 where no sidecar exists) — gate maxima on physiological bounds
  (40-<YOUR_RESTING_HR_BPM>), never "curve ≤ summary".
- **Enum-code mapping: pair real events, don't guess from docs (2026-08-30).** HC
  webhook exercise codes are Android ints, not Samsung's: 79=walk(→1001), 8=bike
  (→11007), 56=run(→1002), 44=bodycombat(→7003), 0=gym(→15002) — mapped by
  nearest-start pairing (gap ≤1 s + duration ratio ≈1.0, N≥2 for the common codes).
  Read actual payload keys before coding (key was `type`, not `exercise_type`);
  label any N=1 mapping "tentative".
- **Cross-source agreement checks: canonical grouping or nothing (2026-08-30).**
  Two manufactured "findings" in one session, both comparator-semantics bugs, both
  caught by structured checks: (a) comparing HC per-session sleep rows 1:1 against
  export night-level rows "diverged" on every fragmented night — group HC sessions
  by the 18h night-key FIRST, then all overlap nights match exactly; (b) comparing
  the HC HR stream's hourly means to export passive-tracker bins "diverged" only in
  workout hours — the stream includes workouts, the bins don't; subgroup-shape of a
  disagreement localizes the semantics gap. An ad-hoc comparison window (21:00–09:00)
  additionally clipped ~96 min of evening fragments and fabricated a dramatic
  cross-surface "Samsung disagrees with itself" claim (retracted in writing). Route
  cross-source checks through the canonical grouping recipe/tool, never a fresh probe.
