# Health/Fitness MCP Server Landscape (gh-verified 2026-08-15)

Discovered via 19 `gh search repos` queries + per-repo `gh api` verification
(metadata, contributors, 30-day commit counts, READMEs, source trees). Session
artifacts: `~/health-mcp-research/FINDINGS.md` + raw evidence files.

## Samsung Health / Health Connect MCP — the field is thin

| Repo | Stars | Last push | Lang | gh license | 30d commits | Contributors |
|---|---|---|---|---|---|---|
| the-momentum/open-wearables | 2342 | 2026-08-14 | Python | NONE | 50 | org-backed (Momentum) |
| davidmosiah/samsung-health-mcp | 9 | 2026-08-12 | TypeScript | NONE | 13 | davidmosiah(27)+dependabot |
| pricejoshua/health-connect-mcp | 0 | 2026-08-11 | TypeScript | NONE | 23 | pricejoshua(44), sole |
| wysie/health-connect-webhook-receiver | 2 | 2026-06-02 | Python | NONE | 0 | wysie |
| Genetrix16/health-connect-mcp | 0 | 2026-05-04 | Kotlin | NONE | 0 | Genetrix16(6), dormant |
| Va1bhav512/healthconnect-mcp | 0 | 2026-05-18 | Kotlin | NONE | 0 | Va1bhav512(5), dormant |

### the-momentum/open-wearables — top finding
- Successor to their 250★ apple-health-mcp-server (README banner announces the move).
- Self-hosted FastAPI+React unifier: Garmin, Whoop, Oura, Apple HealthKit, Google Health
  Connect, Samsung Health (SDK-based via `the-momentum/open_wearables_android_sdk`, Kotlin).
- Bundled MCP server in `mcp/` (stdio via uv): `get_users`, `get_activity_summary`,
  `get_sleep_summary`, `get_workout_events`, `get_timeseries`.
- 441 forks, Discord, docs at openwearables.io, `docker compose up` deploy.
- Trade-off: Samsung path requires running their Android companion app — heavier than
  a CSV export pipeline, but the only org-backed live-sync option.

### pricejoshua/health-connect-mcp — best architecture to fork
- 0★ but 23 commits/30d, 44 total, Vitest tests, Dockerfile, OAuth PKCE, bearer auth,
  dual Node/Cloudflare-Worker runtime.
- Pipeline: HC SQLite export zip → Google Drive → rclone daily cron → local SQLite.
  All 77 HC record types stored raw; `heart_rate_hourly` materialized at sync time.
- 11 MCP tools: `get_health_summary`, `get_heart_rate`, `get_steps`, `get_sleep` (stage
  breakdowns), `get_workouts`, `get_nutrition`, `get_weight`, `list_tables`,
  `get_table_schema`, `query_table` (raw SELECT), `get_last_sync`.
- Homelab personal project — adopt the pattern, not the project.

### davidmosiah "Delx Wellness" ecosystem (current pick's author)
~15 local-first health MCP servers, all actively pushed. Relevant siblings:
- `delx-wellness-hermes` (17★, 20 commits/30d) — Hermes-specific one-command wellness
  profile: WHOOP/Oura/Garmin/Strava/Fitbit/Google Health/Withings/Apple/Samsung/Polar.
- `google-health-mcp` (40★) — Google Health API v4 (Fitbit + Pixel Watch).
- `delx-wellness` (22★) — registry of connectors; `delx-living-body` (0★) — meta-MCP
  composing 15 connectors.
- samsung-health-mcp tools: `samsung_health_connection_status`, `data_inventory`,
  `daily_summary`, `weekly_summary`, `reimport` (auto-promotes newest export zip,
  live re-scan). Productive author, but bus factor 1 and no LICENSE file.

## Best-maintained single-vendor health MCP servers (portable patterns)

| Repo | Stars | Last push | Lang | 30d commits | Notes |
|---|---|---|---|---|---|
| Taxuspt/garmin_mcp | 984 | 2026-08-04 | Python | 19 | 110+ tools, ~90% of python-garminconnect; 10 contributors; most complete health MCP anywhere |
| neiltron/apple-health-mcp | 564 | 2026-08-11 | TypeScript | 11 | npm pkg; DuckDB SQL over CSV exports; 3 tools (schema/query/report); hardcoded 90-day load window limitation |
| r-huijts/strava-mcp | 470 | 2026-06-13 | TypeScript | 0 | 10 contributors; stable/dormant |
| shashankswe2020-ux/whoop-mcp | 140 | 2026-08-14 | TypeScript | 0 | npm whoop-ai-mcp, on official MCP Registry; 14 tools + 4 resources + 5 prompts; heavy Copilot co-authorship |
| akutishevsky/withings-mcp | 36 | 2026-07-27 | TypeScript | 24 | Most actively developed single-vendor server (227 commits); SonarCloud gates; hosted or self-host |
| BerkKilicoglu/google-health-fitbit-mcp | 14 | 2026-08-04 | TypeScript | 4 | Google Health API (Fitbit/Pixel Watch), local OAuth, npm, new 2026-07; README lists Hermes as client |
| PhilipAD/health-export-mcp | 3 | 2026-08-08 | JavaScript | 14 | 190 HealthKit metrics, zero-dep; README explicitly lists Hermes as client |

## Live-data pipeline option (no manual exports)
mcnaveen/health-connect-webhook (phone exporter, 141★) → wysie/health-connect-webhook-receiver
(self-hosted SQLite receiver: raw JSON + normalized sleep + vitals HR/HRV-RMSSD/SpO2/RHR/
respiration) → any generic SQL-over-SQLite MCP. Receiver dormant since 2026-06 but
stdlib-Python simple.

## Search method notes
- Clean results came from vendor keyword queries (`garmin mcp`, `whoop mcp`, `strava mcp`,
  `withings mcp`, `apple health mcp`, `fitness mcp`, `sleep mcp server`, `wearable mcp`,
  `oura mcp`, `fitbit mcp`, `google fit mcp`, plus `health mcp server` / `samsung health mcp` /
  `healthconnect mcp` / `health connect mcp`).
- Topic queries (`topic:mcp health`, `topic:mcp-server fitness`) OR-match loosely and
  returned irrelevant mega-repos (n8n, gemini-cli, awesome-mcp-servers) — poor signal.
- `gh search` has its own 30/min rate bucket, separate from the 5000/hr core API bucket.
- `gh api repos/X/readme -H "Accept: application/vnd.github.raw"` is the reliable README
  fetch; `--jq '.content' | base64 -d` fails on GitHub's newline-embedded payloads.
