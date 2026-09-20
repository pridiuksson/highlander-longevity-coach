# HC Webhook Pull Leg — live architecture + verified semantics (built 2026-08-30)

The continuous-sync leg of the Samsung pipeline, LIVE end-to-end. Mirrors the
runbook `health.health_dir/samsung-data/hcwebhook/PHONE_SETUP.md` (plan of
record); this reference holds the session-verified semantics and pitfalls.

## Architecture (PULL mode, ratified)

```
Galaxy Watch 7 → Samsung Health → Health Connect
    → mcnaveen/health-connect-webhook app (FOSS APK, local HTTP server :8787)
    → [server PULLS over Tailscale] curl 'http://olles-z-fold7.tailed21ea.ts.net:8787/?days=7'
    → POST loopback → wysie receiver (vendored, systemd hcwebhook-receiver, :8787)
    → ~$HEALTH_DB
    → crossmatch_hc_vs_export.py vs $HERMES_HOME/data/health.db (canonical truth)
```

- Push (app→server) is viable over `https://hermes-lightsail.tailed21ea.ts.net`
  (Tailscale Serve, valid cert) but the FOSS APK **blocks cleartext HTTP** despite
  `usesCleartextTraffic="true"` in the manifest — its `network_security_config.xml`
  overrides. Don't re-litigate; pull works and the user prefers it (launch server
  whenever, agent pulls; `?days=N` param extends past the 48 h default).
- Collector: `hcwebhook/pull_hc.py` (GET phone → POST receiver, dedupe-safe);
  verifier: `hcwebhook/crossmatch_hc_vs_export.py`.

## Verified semantics (empirical + source, 2026-08-30)

- **Sleep stage codes (HC ints):** 1=awake, 2=out-of-bed, 3=unknown, **4=LIGHT,
  5=DEEP, 6=REM** (NOT 4=deep — first-guess mislabel; app relays raw
  `stage.stage.toString()`, HealthConnectManager.kt).
- **Exercise codes:** 79=walk (→1001), 8=bike (→11007), 56=run (→1002),
  44=bodycombat (→7003), 0=gym (→15002). Mapped by nearest-start pairing
  (gap ≤1 s, dur ratio 0.998–1.125; 44/0 and the second 56 hit cross-matched
  N=2). Payload key is `type`, not `exercise_type`.
- **HR:** ~1 s stream INCLUDING workout samples; export `heart_rate` table =
  hourly PASSIVE-tracker bins (mean/min/max). Active-hour bins differ by
  construction (gym hour: exp mean 91 vs HC 121); passive hours match within a few bpm.
  Never compare HC hourly means to export bins without excluding workout windows.
- **Body composition DOES sync** (June research doc wrong): weight kg, body_fat
  **PERCENTAGE** (export `body_fat_mass` is a kg MASS — convert kg = pct × weight/100).
  Verified cross-checks (crossmatch checks EVERY snapshot vs export by exact ts): for a
  given snapshot, HC's body-fat percentage × weight must equal the export's
  `body_fat_mass` for the SAME timestamp. That identity is the check; match on the
  timestamp, and re-derive it rather than quoting a pairing from an earlier pass — an
  early pass paired a percentage with the wrong snapshot's mass, and the arithmetic being
  internally consistent did not make the pairing right.
  BMI, height, BMR watts also arrive. Skeletal muscle mass: export-only.
- **Sleep sessions:** HC keeps session fragmentation (evening-doze + main night;
  02:26 splits) that export merges night-level. ANY comparison must first group
  HC sessions by the 18h-anchored night-key — all 6 overlap nights then MATCH
  exactly (≤1 min rounding). Ad-hoc windows (21:00–09:00) clip fragments and
  manufacture fake cross-surface disagreements (cost one retracted "B′ observed
  in the wild" claim).
- **Steps: MIXED GRANULARITY — never sum windows.** HC serves a full-local-day
  AGGREGATE window (running total) PLUS fine delta windows whose spans sit INSIDE
  it. Daily total = the midnight-anchored FULL-DAY window only; summing windows
  double-counts (a verified trap). Labels are Stockholm-LOCAL calendar day
  (22:00Z in CEST / 23:00Z in CET; fold day = 25h window), not the UTC start
  date. No export daily-step table → HC-first.
- **NOT delivered via HC (export-only):** HRV/RMSSD (key absent from payload —
  Samsung doesn't expose continuous HRV to HC), 1 Hz workout sidecars.

## Dedupe semantics (two layers, different identity)

- `raw_events`: keyed on payload sha256 — identical re-pull still INSERTS (bytes
  differ via timestamp); correct, it's a byte-exact archive.
- `vitals`/`sleep_sessions`: keyed on record identity — stay EXACTLY stable
  across overlapping pulls (verified: raw_events grew, vitals 36,794 unchanged).
  Downstream analysis reads the normalized layer → no double-counting.
- **CROSS-PAYLOAD session dedupe is MANDATORY in any parser** (2026-08-30, caught
  by gate H2 on the first parse run): every pull RE-SERVES the same sleep/exercise
  sessions, so a parser that just sums payloads over-counts N× (nights summed ~6×
  before the fix). Dedupe sleep sessions by `session_end_time` and exercises by
  `start_time` across all archived payloads. The raw_events byte-archive keeps
  duplicates by design; only the normalized layer must dedupe. Parse pipeline:
  `hcwebhook/parse_hc_sqlite.py` (→ `$HERMES_HOME/data/health.db`, gates H1–H6),
  `hcwebhook/hc_sync.py` (pull → crossmatch → parse), `hcwebhook/hc_watchdog.py`
  (staleness alert, silent-when-healthy; cron job hc-pull-staleness-watchdog).

## Ops notes

- Play Store listing is a paid flavor; FOSS APK free from mcnaveen GitHub
  releases (`app-foss-release.apk`, v1.9.17 2026-08-28).
- Receiver token: `~/.local/share/hcwebhook-receiver/webhook_token` (chmod 600);
  endpoint `/health-connect/the user`; `X-Webhook-Token` header.
- `sudo tailscale serve --bg --https=443 http://127.0.0.1:8787` needs tailnet
  HTTPS certs ENABLED in the admin console (else `serve` hangs, "not enabled").
- Approval-gate notes for this environment: server→phone curl may require user
  approval (outbound to device); DB writes via heredoc blocked — write script
  files (`~/tmp/*.py`), run them.
- Receiver `vitals` UNIQUE key includes `value` (upstream, vendored unmodified) —
  a bpm-scale jitter on the same second across pulls would dup a row; negligible
  at 1 Hz today, patch on next re-vendor.
- Export `body_composition.ts_local` is stale-UTC-labeled (extras-parser family
  missed by the 08-16 tz fix) — never coach/derive from that column; cross-match
  HC body against export `ts_utc` instead.

## Post-2nd-peer-review hardening (2026-08-30, deleg_648c2ac3)

- **Crossmatch HR verdict:** compare HC hourly means to export bins on the PASSIVE
  hour subset only, and TOLERATE the export's final ingested hour — it's a partial
  bin (full HC hour vs a truncated export hour is not a divergence; without this the
  tool reports DIVERGE on every run forever). Active-hour diffs are expected by
  construction (HC stream includes workouts, export bins don't).
- **hc_sync.py exit codes:** 0 = fully green, 1 = parse/crossmatch failed, 2 = phone
  pull failed but cache still parsed (stale-cache run). Don't collapse 2 into 0; the
  operator must know data isn't fresh.
- **hc_watchdog.py reachability:** treat ANY HTTP response (204/404/etc.) as "phone
  reachable"; only a connection-level failure (timeout/refused/DNS) is "unreachable".
  The receiver 404s unknown routes by design — a 404 must never count as the phone
  being down.
- **Parser dedupe must be BOTH in-memory and DB-constrained.** Gate H2 (phys band)
  catches sleep over-counting; exercises need an explicit `UNIQUE(start_utc, hc_type)`
  + a row-count == distinct-start_time gate so a dedupe regression fails loudly
  instead of silently 6×-inflating.
- **Gate honest to its docstring:** H3's "dur in [30, 4*3600]" needs BOTH bounds
  checked (code originally only checked the max; the min bound is a real signal —
  sub-10s records are bogus auto-captures).
- **Dedupe-key granularity must match the DB PK granularity** (second-truncated vs
  microsecond) or same-instant legitimate measurements collide/merge incorrectly.
  Standardize both on second-truncated.
