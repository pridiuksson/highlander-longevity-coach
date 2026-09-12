# Withings Public API — verified facts for direct pulls

Verified 2026-09-01 against official sources. Complements
`references/withings-integration-landscape.md` (third-party tools / export ZIP);
this file covers pulling data straight from Withings' own API.

**Sources (primary):**
- `https://developer.withings.com/llms.md` — official one-file AI-agent reference, linked from `https://developer.withings.com/developer-guide/v3/ai-agent`
- `https://developer.withings.com/openapi.yaml` — OpenAPI 3.0.3, 63 paths, server `https://wbsapi.withings.net/`
- Guide page `https://developer.withings.com/developer-guide/v3/integration-guide/public-health-data-api/get-access/oauth-authorization-url/` (scope→webservice table)

**Portal gotchas:** `https://developer.withings.com/api-reference/` is a Docusaurus
JS shell — no static content for plain extraction. Old `developer-guide/v3/...`
URLs (e.g. the advanced-research oauth-web-flow page) now redirect to the Partner
Hub home; only some guide paths still render. Use llms.md + openapi.yaml instead.

## Auth (llms.md "Authentication"; openapi.yaml `oauth2-authorize`)

- Authorize: `GET https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=…&scope=…&redirect_uri=…&state=…` (`&mode=demo` = demo user, no device needed).
- Token + refresh: `POST https://wbsapi.withings.net/v2/oauth2`, `action=requesttoken`, `grant_type=authorization_code|refresh_token`, form-encoded.
- Lifetimes: access_token **3 h**; authorization code **30 s** (exchange immediately); refresh_token **1 year**.
- **Refresh tokens ROTATE**: every refresh returns a NEW refresh_token; the previous one dies **8 h** later. Persist the new token on every refresh or you lose access. Access token expiry surfaces as error `343` (llms.md refresh-on-343 pattern).
- Scopes: `user.info`, `user.metrics`, `user.activity`, `user.sleepevents`.
- **No public-client / PKCE flow** — client_secret required on every token exchange, so token refresh must run server-side. redirect_uri must be registered as "Callback Url" in the app (dashboard: `https://developer.withings.com/dashboard/`).

## Endpoints (all POST, form-encoded; envelope `{status, body}`, `status=0` = OK)

Base: `https://wbsapi.withings.net`. Pagination where offered: response `more:1` + `offset:XX` → re-call with `offset` until `more=0`. Sync pattern: prefer `lastupdate` (unix ts) over startdate/enddate; response `updatetime` is the next call's `lastupdate`.

| Service / action | Data | Range params |
|---|---|---|
| `/measure` getmeas | weight, height, fat mass/free/ratio, BP, HR, SpO₂(54), temp, ECG(130); `meastypes` comma list; value×10^unit | `startdate`/`enddate` or `lastupdate`; offset |
| `/v2/measure` getactivity | daily steps, distance, elevation, calories+totalcalories, HR avg/min/max+zones | `startdateymd`/`enddateymd` or `lastupdate`; offset |
| `/v2/measure` getintradayactivity | intraday activity series | `startdate`/`enddate` unix |
| `/v2/measure` getworkouts | workouts: calories, intensity, HR fields | `startdateymd`/`enddateymd` or `lastupdate`; offset |
| `/v2/sleep` get | per-night stages (deepsleep/lightsleep/remsleep duration), HR, `spo2_average`, RR, snoring | `startdate`/`enddate` — **max 7-day span per call**, loop for more (openapi.yaml param desc) |
| `/v2/sleep` getsummary | daily sleep summaries: sleep_score, total_sleep_time, efficiency… | `startdateymd`/`enddateymd` or `lastupdate` |
| `/v2/heart` list → get | ECG/AFib recordings; list then fetch signal by `signalid` | list: `startdate`/`enddate`; offset |

HRV appears in llms.md's sleep-endpoint data list but the exact data_fields name was not pinned down — check openapi.yaml `sleepv2-get` data_fields enum when needed.

## Rate limits

- **No numeric published limit.** llms.md guidance: poll ≤ once/10 min/user; prefer webhook + pull-on-notify. `status 601` = Too Many Requests.

## Webhooks (Notify API)

- `POST /notify` `action=subscribe&callbackurl=…&appli=…` (Bearer auth works; signature/nonce is the alternative). appli: 1=body metrics, 4=sleep, 16=BP, 44=ECG, 46=activity, 54=AFib PPG.
- **Trap:** appli namespace ≠ meastype namespace — `appli=54` (AFib) is unrelated to `meastype=54` (SpO₂).
- Push payload to your callback: `userid`, `startdate`, `enddate`, `appli` (a window, not the data) → then fetch that range. Also `action=list|get|update|revoke`.

## Backfill / retention

- No documented limit on historical depth found in llms.md or openapi.yaml (absence, not confirmation). Full history = date-range calls + offset loops; `lastupdate` for incremental sync.

## Spec

- Downloadable OpenAPI 3.0.3: `https://developer.withings.com/openapi.yaml` (verified HTTP 200).
