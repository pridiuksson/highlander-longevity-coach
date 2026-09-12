# Worked case: auditing sleep-extraction bedtime math + medians (2026-08-16)

Repo `highlander-longevity-coach`, `<YOUR_HEALTH_DIR>/`. Ten-year sleep "pattern" extraction: `sleep_extract.py`
+ `fix_p3.py` (Samsung stage-minutes recompute) feed `sleep_patterns.json`. This audit
checked **calculation correctness only** (chart out of scope), read-only against:
`$HERMES_HOME/data/garmin.db` (sleep_night, mode=ro) and `$HERMES_HOME/data/health.db` (sleep_session, sleep_stage).

## Authoritative conventions (per repo verified tooling, never guessed)
- Samsung stage codes: 40001=wake, 40002=light, 40003=deep, 40004=REM.
- Samsung night-key `NK` = `substr(datetime(substr(start_local,1,19),'-18 hours'),1,10)`.
- Samsung per-night stages = SUM over **all session fragments** of that night (night-keyed);
  duration = sum of ALL stage rows (includes wake, within-device only).
- Garmin `total_s` = sleep time EXCLUDING awake; NO `rem_s` (all NULL); 2016/17 mostly
  `has_stages=0`; `calendar_date` = wake date; era tz = Europe/Vilnius (`start_utc` is UTC).
- "Bedtime" = minutes after 18:00 local of night-start (wraps past midnight).

## Independent-probe template used
For every metric: write MY OWN SQL (night-keyed), aggregate, median; compare to the json.
No trust in "the script runs." All probes written to `/tmp` files and run as scripts
(heredocs are consent-gated for subagents).

## Results (all headline numbers reproduced)
- 2024-07 Samsung deep-min median 61.5 = json 61.5 (anchors 60–63 ✓); bed 297 = 297.
- 2019-06 Garmin bed 432 = 432; dur 7.31 = 7.31.
- Yearly bed medians 2021 330 (23:30) / 2022 314 / 2025 256 (22:16) all reproduce = doc claim.
- REM coverage 124/126, 356/356, 361/361.
- fix_p3 (monthly_min): 2110 rows = 2110 distinct (nk,uid) → **no double counting**;
  0 uids span >1 NK; 4 rows with `u=0` excluded; 2025-08 deep 77.5 = json 77.5.

## Defect found (minor, isolated)
`sleep_extract.py:23` `bed_minutes_local()` = `m-1080 if m>=1080 else m+360` — correct
full-day circular mapping (= `(m-1080)%1440`), but returns out-of-window values 720–1439
for night-starts in 06:00–17:59 local. 9/1336 Garmin nights (0.7%) fall out-of-window;
**8 cluster in 2018-03** (07:29–10:34 local, 8 consecutive days → daytime/nap sessions),
dragging that month's bed median 388 → **438** (+50 min). Garmin-era yearly bed shifts only
+4 (427 vs 423). Fix: add a window guard / exclude non-nocturnal starts, or clamp 0..720.

## Framing caveat (not a defect)
Samsung data begins **2021-08**, so "year 2021" stats are Aug–Dec 2021 only — the
23:<value>→<value>:16 trend compares a partial year vs full years. Quote with the caveat.

## Probe pitfalls self-caught this session (see SKILL.md section)
- `min(bed(fragment))` vs `bm_nk(min(m))` — wrap must be applied per-fragment then min'd;
  min-reclock-then-wrap gave FALSE 339 vs true 330 until corrected.
- ISO month-key slicing: `'2019-06-30'[:6]` == `'2019-0'` (need `[:7]`). Two probes silently
  emptied their month samples.
- Spot-checking a single DST day is not enough — convert a full winter + full summer month.
- Cross-check coverage of partial years (data may start mid-year) before trusting a year-level trend.
