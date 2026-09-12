# Sleep-architecture pattern mining — method v2 + verified 2026-08-29 results

Session: deep-sleep strata (>50/>90 min), day-before drivers, deep↔REM coupling,
2021-2026. Analyzer: `<YOUR_HEALTH_DIR>/samsung-data/deep_sleep_patterns.py`
(v2, peer-reviewed); deliberation brief `DEEP_SLEEP_DELIB_BRIEF.md` (5 corrections
recorded); runbook finding 3 v2.1.

## Method checklist (v2 — each item exists because its omission produced a WRONG headline first)

1. **Night key on the FULL timestamp**: `(start_local − 18h).date`, never
   date-only. Date-only keys split a late-evening session from its morning
   continuation across two keys → fake "16.8h nights" with 167 min deep.
2. **Main-sleep filter ≥3h**: naps (392 sessions / 651h in this DB) must not
   pile onto night keys. Report nap rate BY day-type (0.08–0.21/night here) —
   dropping naps is only safe if nap rates are balanced across groups.
3. **Durations from `*_utc`** (julianday diff): DST-immune real elapsed time.
   Keys stay `*_local` (lived-clock, house rule). Run the local-vs-utc
   key-mismatch diagnostic: 11/2,180 = 0.5% here — the tz concern is testable,
   don't argue it.
4. **Day-before attribution = the night key's own date.** Night key D spans
   D-18:00 → D+1-18:00, so the preceding daytime IS calendar date D — morning
   AND evening sessions on D precede that night. An off-by-one here (crediting
   runs to night D+1) INVERTED the run effect before it was caught by
   reconciling against a prior verified result.
5. **Reconcile with prior verified numbers before publishing** (e.g. run
   55.7 vs re-audit 56.4, baseline 52.5 vs 52.1). Agreement = pipeline
   validated; disagreement = find the method difference first.
6. **Means AND tail, with rigor**: group means + P(threshold) + Fisher exact
   on the tail + permutation test on the mean delta + bootstrap CI. A mean
   effect can be null (run-day +3.9 min, p=0.13, CI [−4.5,+12.5]) while the
   tail is enriched (deep≥90: 6/43 run vs 5/196 non-run).
7. **Multiplicity fair family**: correct only over the pre-registered strata
   (groups × thresholds actually hypothesized — here ×8 → p=0.039 survives),
   report the exploratory family separately (×<value>→<value>). Never Bonferroni
   over everything ever printed.
8. **Era-stratify strata against known step dates.** 2026 strata straddled the
   Mar-2026 cohabitation step: 5/6 "run-tail" nights were pre-cohab, run-night
   deep fell <value>→<value> across it while non-run fell only <value>→<value>. The
   "tail effect" was era-confounded (cohab suppresses exercise→SWS response,
   or Jan–Feb small-window luck, n=9). **Check every within-year contrast
   against the cohab/relocation/firmware step ledger before believing it.**
9. **Duration-band control** for any day-type group comparison (compare within
   7.0–7.5h nights): the e-bike-commute "floor" (47.9 vs 52.5 raw) collapsed to
   ~−2 min noise in-band — it was a shorter-nights artifact, not a modality
   effect.
10. **Correlations: intersect keys** (a key present in deep but not rem would
    otherwise silently drop from one array only), report raw + partial-given-
    duration via residualization, and split by era. Coupling that DECAYS across
    years (+0.21 → +0.20 → +0.14 → ≈0.00, 2021→2026) at flat duration is an
    algorithm-maturation signature: early-era stage coupling is device
    artifact; the modern-era answer is deep ⊥ REM given duration.

## Verified results (2026, clean keys; multi-year in the year table)

- Baseline 2026: deep 52.5 min median 51.5, P(≥50) 53%, P(≥90) 5%, REM 110, dur 7.03h.
- Run-day mean NOT established; run-tail era-confounded (see #8); evening-hard
  sessions SAFE not beneficial (50.9 vs 55.9 morning, p=0.73 — the old
  "hard evenings help 57.4 vs 51.2" claim was window-specific and fails
  clean-key reproduction).
- deep↔REM: modern-era partial ≈ 0.00 (stage competition; REM is the
  duration-elastic stage — the 2024 REM<deep spike, 12% of nights, is
  short-night compression: those nights averaged 6.12h vs 6.54h year-mean,
  median flip only 12 min. Not firmware.)
- Multi-year deep <value>→<value> min (2021→2025) at FLAT 6.5–7h duration is
  share growth, but rides device-algorithm maturation (2021 deep share 5.8%
  physiologically implausible) — never treat pre-2023 absolute minutes as
  physiology; 2026 cohab step (−9) sits on that uncertain baseline.

## Deliberation integration

Feed such analyses to the deliberate skill as a written brief with a
**corrections ledger**: corrections discovered mid-deliberation (here: 5, incl.
the post-phase-2 era-confound) get appended to the brief + debate.json with
explicit OVERRIDE instructions to later-phase agents. All corrections were
conservative downgrades — a mid-flight correction that would INFLATE a claim
warrants re-running earlier phases instead.
