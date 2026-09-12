# Samsung Health Tooling Landscape (research 2026-08-15)

Condensed from `~/highlander-longevity-coach/Knowledge/Research/Tech/samsung-data-import-landscape.md` (commit 5d0f0ce) — that doc is the full record; this is the operating summary for future sessions. All repo metadata was verified via `gh api` on 2026-08-15.

## Validated architecture (unchanged by round 2)

Historical leg (LIVE): `samsung-health-mcp-unofficial@0.7.3` over CSV/zip exports.
Daily leg (NOT BUILT): mcnaveen/health-connect-webhook app on the phone → JSON POST → adapted wysie receiver → SQLite. Health Connect retains only ~30 days of granular data — the CSV export remains the only source of full history.

## Adopt verdicts

| Tool | Verdict | Why |
|---|---|---|
| mcnaveen/health-connect-webhook (141★, AGPL, active) | ADOPT (daily leg) | 24 HC data types incl VO2max (verified in docs/webhook.md); foreground service; POST or local HTTP :8787 |
| wysie/health-connect-webhook-receiver (2★, MIT, Python stdlib) | ADOPT (server half) | Webhook → SQLite, token auth, dedupe, sleep/vitals normalization; README targets Galaxy Watch via Samsung→HC. Fork-adapt, don't depend |
| davidmosiah/samsung-health-mcp (9★, MIT, 13 commits/30d) | ADOPTED (historical leg) | Wired + pinned in main profile. Bus factor 1 but author ecosystem is real (~15 local-first health MCPs) |
| Devasy/samsung-health-sdk (PyPI, MIT, pandas) | Reference | DataFrame API + HRV/sleep feature engineering if Python-side analysis needed |
| v-2841/samsung-health-export (MIT, stdlib-only) | Reference | Whole-export → JSON with per-type coverage manifest; completeness cross-check |
| joaoruimatos/samsung-health-to-garmin (GPL, pushed 2026-08-14) | Reference | Handles newest export-format quirks (exercise.extension/route/weather) if the MCP chokes on 2026 exports |
| the-momentum/open-wearables (2342★, MIT, org-backed) | WATCH | Multi-provider FastAPI + bundled MCP; Samsung path needs their unlicensed Kotlin companion app. Graduation path if Whoop/Oura/Garmin ever enter the picture — overkill today |
| HCGateway (414★) | SKIP | Dormant since 2025-12, MongoDB dependency |
| wger / FitTrackee / Endurain / GarminDB / jimmykane | SKIP | None natively ingest Samsung; wrong data shape or single-user overkill |

## delx-wellness-hermes — deep-dive verdict (source-read)

Installer/orchestrator, NOT a data tool. Its Samsung connector IS `samsung-health-mcp-unofficial@0.7.3` — zero new capability. Hard-refuses writing into the default Hermes profile (`install.ts:40`) → forces a separate wellness profile that would wall data off from the coaching agent. Generic SOUL, no Phase 2 / 4×4 / zone-2 context. SKIP as product.

Patterns worth keeping: (1) version-pin MCP packages, no floating `-y latest`; (2) non-destructive config merge + timestamped `.bak` before writes; (3) "agent-safe-series" — capped time-series query tools over raw stream dumps (apply to the future receiver's query layer).

## Known data gaps (Samsung → Health Connect)

NOT synced: body composition (skeletal muscle, body water), ECG, stress, floors, continuous watch HR (delayed — only manual measurements sync immediately). VO2max IS covered by the webhook. the user's skeletal-mass tracking stays manual (periodic CSV export).

## Research method that worked (reusable)

5 parallel leaf subagents, each a keyword domain, all querying GitHub via `gh search repos` + `gh api` (no web fetching, keeps orchestrator context clean). Give each: already-evaluated list + known-dead list (no re-reporting), verify stars/pushed_at/license/archived via api not README. Then OWNER-verify top candidates — round 2 caught one factual error (VO2max claim) and license-field noise this way. Raw evidence dirs from that run: `~/hc-search/`, `~/gh-health-search/`, `~/health-mcp-research/`, `~/samsung-health-github-findings.md`.
