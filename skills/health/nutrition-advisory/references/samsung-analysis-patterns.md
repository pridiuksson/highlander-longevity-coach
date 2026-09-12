# Samsung Data — sqlite Analysis Patterns

Companion to `references/wearables-data-reliability.md` and the canonical runbook `<YOUR_HEALTH_DIR>/samsung-verified-data.md` (confidence tiers, parse gates, audit residuals). Read the runbook first; ALL parse gates must pass before any advice is drawn from the DB. The `samsung-health-import` skill owns refresh/wiring.

**DB:** `$HERMES_HOME/data/health.db` (gitignored). Stage codes: 40001=awake, 40002=light, 40003=deep, 40004=REM — correlation-validated 2026-08-15; NEVER re-derive by plausibility (the plausible-share mapping had deep/REM swapped).

## Hard rules (each one bit a session)

- **Night-keys, never raw calendar dates:** `substr(datetime(substr(start_local,1,19), '-18 hours'),1,10)`. `ts_local` mixes Vilnius/Stockholm eras (EET before 2025-09-08, CET after — dual-timezone data, reconciled in audit); raw date grouping mis-buckets nights.
- **`fetchall()` before per-row Python work.** A nested per-row subquery executed on the SAME cursor that is iterating the outer loop silently invalidates it — returns n=0 with NO error. Separate cursors or materialize first.
- Schema: workout columns are `calorie` (not kcal), `mean_hr`, `distance_m`; export-CSV durations are milliseconds (parser normalizes to seconds in sqlite).

## Within-night positional analysis (sleep architecture)

- Anchor t0 at the **first scored sleep epoch** (first non-awake stage row), NEVER session/lights-out start — lights-out anchoring inflates the first third with wake and manufactures fake "early-REM" findings.
- Thirds: `min(int(3 * seconds_since_t0 / span), 2)`.
- **Bout reconstruction:** sort epoch rows by time; merge consecutive same-code rows into bouts — across session fragments (nights are multi-fragment: watch + phone segments). Classify each bout's termination by the NEXT epoch's code (awake-terminated vs stage-shift). Bout-median-by-third is the core architecture read (textbook: REM bouts lengthen T1→T3).

## Verified probe patterns (2026-08-15)

- **Good/poor quartile enrichment:** split nights into top/bottom quartile by a target metric (e.g. deep minutes) → measure day-type enrichment (run/gym/class/walk/rest) in each. Finding for this profile: deep sleep is modality-driven (run days 2.2× enriched), volume- and timing-neutral. **Control for night duration before drawing protocol conclusions** — two methods, both used 2026-08-15: (a) within-duration-stratum split (median TIB → re-test inside each half; the run-day enrichment survived 50% vs 23% short, 38% vs 25% long), (b) duration-independent metric (stage as % of stage-total, not absolute minutes). An uncontrolled enrichment finding is provisional until one of these runs.
- **Estimate-revision check (sliding anchor):** when ONE watch metric contradicts two independent anchor series (e.g. VO2max↓ while RMSSD↑ + RHR↓), query the device's own revision history (`hr_threshold` AT/AnT/max ladder) BEFORE believing either side. VO2max <value>→<value> resolved as max-HR <value>→<value> re-anchoring — the cliff landed 60 min after a revision, same day. Query the ladder on ANY-threshold change, not max-HR only (AT kept sliding for months after max froze).
- **Device-fork check:** group series by `deviceuuid` month-by-month to exclude hardware change before attributing a step change to physiology. **Firmware-fork check (2026-08-15, run-005):** the export itself carries NO version stamps (10 tables, no version/firmware columns; `7000107` in CSV headers is Samsung's export-FORMAT version, constant across files; only ~7 `sleep_raw_data` JSON blobs, none historical) — the data side can only date the STEP, never identify the software. Settle firmware forks by correlating step date with the PUBLIC update timeline (delegate a researcher with the arbitration windows + decision rule: update within ±2 weeks of the step materially strengthens firmware), then run a **step-shape probe** (weekly medians of the exact anomaly metric around the candidate date): a scoring-model swap produces a discrete 1-2-week jump; a gradual ramp/tail-driven shift argues environmental. Calendar collision alone overstates the case — run-005 found One UI 8 Watch EU rollout (2025-10-20) dead-center in the REM-step window BUT no discrete step at that date (era gap tail-driven, late-Dec cluster instead). Watch-side install dates (Settings → About watch → Software update history) remain the gold standard.
- **Era-mean tables before two-step attribution:** when a decline has two candidate causes at two dates, compute per-era MEANS (Vilnius 65.4 → settle 64.5 → cohabitation 56.1 min deep at IDENTICAL in-bed time — only the last persisted) before assigning persistence — run-005: the Oct-Nov relocation deep-dip looked persistent in the step analysis but the era table showed it TRANSIENT (settled back to baseline within the settle era); only the cohabitation step persisted. Step detection and persistence attribution are different questions.
- **Cohort splits that matter for this profile:** pre/post cohabitation (~2026-03-01), Vilnius/Stockholm eras (split 2025-09-08), training-modality days.
- **Bout-metric selection:** whole-night REM-bout counts and later-third bout counts are DIFFERENT metrics and can disagree — this profile's whole-night counts never stepped (oscillated 10-13 across the whole period) while later-third counts defined the verified anomaly. Always bin the exact metric the anomaly was established on; whole-night proxies dilute positional effects. Also state the metric's per-night SD (measured, not assumed) before claiming a detection window — run-005 assumed REM-bout SD ≈3; measured 4.0-4.5 (whole-night, 2025-2026 eras), which still supported the 2-week read but with wider CIs.

## Known residuals (do not re-litigate)

- RMSSD↔sleep-duration correlation ≈ 0 (609 nights) — never build duration advice on this pairing.
- VO2max quarantined (LOW-CONFIDENCE, artifact-resolved); stage splits are consumer-grade (trend-only); AT/AnT absolute values are sliding device estimates — field-validate (talk test) before any zone-based training use.
