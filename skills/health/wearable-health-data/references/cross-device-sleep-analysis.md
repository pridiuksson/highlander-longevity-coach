# Cross-device sleep & activity analysis (Garmin ↔ Samsung)

Session-verified rules for analyzing/cross-comparing the unified decade dataset
($HERMES_HOME/data/garmin.db + $HERMES_HOME/data/health.db). All verified 2026-08-16 against raw SQL;
evidence scripts live in `highlander-longevity-coach/<YOUR_HEALTH_DIR>/decade-sleep/`
(`tz_dst_discriminator.py`, `tz_overlap_anchors.py`, `tz_probe.py`,
`crossmatch3.py`, `scrutinize.py`).

## Timestamp conventions — one export, TWO conventions (both sleep frames = TRUE UTC)

| Field family | Convention | Proof |
|---|---|---|
| Garmin sleep `sleepStart/EndTimestampGMT` | **TRUE UTC** (the name meant what it said) | FOUR independent anchors — see below |
| Garmin workout `begin_gmt` | **true UTC** | begin_local−begin_gmt bifurcates +1h winter / +2h summer (CET/EET DST pattern) |
| Garmin `daily_summary` wellness windows | ≈ true UTC | window edges align with UTC day boundaries |
| Samsung 2026-format CSV strings (ALL families) | **TRUE UTC**; `time_offset` = local offset | sidecar-json epoch millis == CSV strings (see `timestamp-timezone-truth.md`) |

**Garmin-sleep anchors (2026-08-16 evening, survived adversarial peer review):**
1. Overlap week: night 2021-08-<value>→<value>, both devices worn — Garmin 21:42 vs
   Samsung-native 22:18 both-as-UTC = 36 min apart; under local reading Garmin
   detects sleep 3h36m BEFORE the other wrist (impossible).
2. Wake testimony: strings-as-UTC → wakes 06:45–07:45 local (user ~06:40).
3. Workout-gap: median sleep-end→first-workout +1.48h (n=228, per-night
   pairing); local reading drives the median NEGATIVE (workouts before sleep
   ended) — physically impossible. (An earlier +0.7h/n=218 figure came from a
   looser pairing; always re-derive per-night.)
4. **DST seasonal shift (sharpest, immune to watch-clock state):** Vilnius
   +2↔+3 flip ⇒ UTC strings predict ~+1h winter-vs-summer shift in wake-string
   medians, local strings predict ~0h. Measured **+1.13h** (summer 06:16 /
   winter 07:23, n=361/346).

**Three-reading saga (kept as the cautionary tale):** local → UTC → local →
UTC. Both reversals came from reasoning off another column whose own
convention was unproven. The morning "local-display" proof leaned on the
handoff night's identical-minute match to Samsung — **circular**: that row is
a healthsync import that COPIED the Garmin string into a UTC column, proving
the importer assumed UTC, not that Garmin emitted UTC.

**Frame-discrimination rule (class-level):** settle a timestamp-convention
question ONLY with mechanical anchors — (a) epoch millis in sidecars, (b)
same-night multi-device overlap, (c) user testimony on known wake times,
(d) downstream-impossibility tests (negative gaps), (e) DST seasonal-shift
medians for DST regions. NEVER another unproven column, NEVER field-name
semantics, and NEVER a verbatim import-copy (circular).

## Provenance traps

- **One imported night in Samsung data**: NK 2021-08-25 is Samsung Health's
  one-time import of Garmin's 2021-08-26 row (Connect→Health sync on watch
  setup day). Signature: the only window night with all four native scoring
  columns NULL (efficiency, sleep_cycles, physical_recovery, mental_recovery)
  + stages identical to the minute. Exclude from Samsung-native analyses —
  and never use it as a tz anchor (see circularity above).
- **Samsung provenance strata**: phone-staged 2021-08..2022-09 vs
  watch-staged 2022-10+ (schema has no device column — only datauuid — so
  era-based strata is the ceiling).

## Device-capability stratification

- Garmin device 2016-2021 = **Fenix 3 HR**: accelerometer-only two-class
  sleep staging; **REM absence is a hardware certainty** (pre-dates Firstbeat
  HR-based staging). Deep shares 46-56% = movement-splitter artifact, not
  physiology.
- Cross-era stage comparisons (Garmin deep vs Samsung deep) are INVALID —
  different constructs, no published transform. Only **bedtime, wake time,
  duration** survive the device handoff. Within-era trends + TST are fine.
- Cross-device join validated once: handoff-week bedtime agreement 18 min.

## Comparison hygiene

- **Never compare full-year aggregates to a partial year.** Cut BOTH periods
  to the identical calendar window (pattern: `yoy_2025_2026.py` — Jan-1..Jul-3
  both years). Full-2025 vs 7-months-2026 looked flat (+2%) while the matched
  window showed the real story (conscious tier +113%).
- **Out-of-window filter must be symmetric**: exclude <18:00 / ≥06:00 starts
  from bedtime stats on BOTH sources (Garmin 4 nights, Samsung 64 nap/daytime
  fragments). Asymmetric filtering = the exact kind of asymmetry peer review
  catches.
- **Night-key**: Samsung NK = start_local − 18h (canonical); Garmin
  calendar_date = wake date; alignment between them is +1 day.
- **Don't flip a published number on a third reading without a NEW mechanical
  anchor.** Retraction debt compounds: freeze the artifact (chart, runbook),
  name the missing discriminator, resolve it, then flip once with the full
  evidence chain. The peer-review loop that settled this one: re-derive every
  anchor yourself from source → hand the peer PRIMARY DATA + the inference
  chain (not your conclusions) → demand it name the weakest anchor and any
  circularity → execute its demanded mitigation yourself → publish negatives
  (the RHR-in-window test was weak, 13.2% vs 10.0%, and is recorded as such).

## Samsung exercise-type codes — official SDK table first

Codes are PUBLIC Samsung SDK constants (`references/exercise-type-codes.md`,
97-entry table + refetch recipe), not account-specific. The user-verified
overlay (runbook rule 8): 1001=auto-walk, 1002=run, 15002=gym-strength,
11007=bike (distance=regular, no-distance+2026-Stockholm=e-bike commute),
9002=Bikram yoga, 10007=circuit-training (coaching-program source), 15005=
treadmill walk/jog (manual). Unknown code → SDK table first, then ask the
user. Never guess from another vendor's schema.
