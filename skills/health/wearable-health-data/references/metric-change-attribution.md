# Metric-Change Attribution: why did a wearable-derived metric move?

**REV A 2026-08-30** — rewritten after the original worked example (run-008, Aug
deep-sleep collapse) was partially VOIDED by post-deliberation audit. Two of its
three fingerprints failed verification. What changed: the unscored-gap "smoking
gun" is demoted to hypothesis-only; GATE ZERO (input-series verification +
testimony anchor) added; fragment contamination documented; percentages withdrawn
in favor of co-leading hypotheses.

Worked example: 2026-08-30 Aug deep-sleep collapse, weekly deep <value>→<value>→~30 min at
flat efficiency/latency. Collapse REAL; original ranking (B restage 58-65% /
A bedtime 20-22% / C load 15-20%) VOIDED; REV A verdict: B' (classifier
re-label) / C (chronic load) co-lead, A eliminated, no percentages.

## Candidate causes (the standard triad)
- **A — timing/circadian/behavior** (bedtime shift, phase misalignment, cohab,
  environment).
- **B / B' — device algorithm restage or re-label** (scoring-model re-weighting,
  retroactive re-analysis; known ratchet history: max-HR ladder, VO2max slide,
  HR thresholds revised repeatedly).
- **C — training load / stress** (new modality workload, HRV dip, illness).

## GATE ZERO — verify the input series BEFORE any panel or ranking (2026-08-30 lesson)
The 4-expert panel voted 4-0 on rankings built from two series that later failed
verification:
1. "Bedtime advanced 2h (May 03:21→Aug 23:21)" — a naive non-circular median of
   clock strings WITH sub-3h fragments included. True bedtimes were FLAT all
   summer (~00:07-00:23 local medians). One sentence of user testimony ("23:20-
   23:40 for at least a year") falsified the whole series; a bug-recipe probe
   (fragment-contaminated naive median) reproduced the fake values.
2. "~30 min/night unscored gap" — never existed per-night (staged = measured,
   median gap 0.0; only 2/29 Aug nights lacked stage rows = not-yet-analyzed).

Gate procedure: (a) list every load-bearing series (the ones hypotheses stand or
fall on); (b) re-derive each from raw with canonical time tooling — circular
18:00-anchored medians, longest-≥3h-session bedtime, NEVER naive clock-string
medians; (c) testimony-anchor check: "does this match lived experience?".
Testimony beats a buggy probe; a probe that reproduces beats testimony.

## Fingerprint hierarchy (post-REV A)
- **RE-LABELING inside fully-staged nights** (deep share ↓ while light share ↑,
  staged total FLAT) = classifier relabel. The verified real-world fingerprint
  (Aug 2026: deep share <value>→<value>%, light +35 min, REM +1.8 pp, total flat).
  Biology redistributes; a RELABEL moves minutes between stage buckets without
  changing the total.
- **UNSCORED-time emergence** (staged total falls at flat measured duration) is
  a plausible restage hypothesis but MUST be re-derived per-night from raw
  before use. Monthly-aggregate medians can fake it. In its only field test it
  did not exist.
- **Re-import byte-diff of identical night-keys** remains the DECISIVE test for
  restage: drift on re-analysis of persisted nights ⇒ restage; byte-stable +
  persistent drop ⇒ physiology.

## Fragment contamination (sub-3h sessions are NOT naps)
Sub-3h sleep sessions are detection artifacts unless proven otherwise: evening
pre-sleep wind-down segments (ending 11-76 min before main-sleep onset), night
splits, post-wake dozing. Field audit (2026-08-30, user "does not nap ~1×/yr"):
only 23/392 fragments started in the 12-18 nap window across 5.5y; 147 were
evening 18-24. Including them in naive medians fabricated the fake "4-month
bedtime advance". Before ANY time-of-day series: main-sleep filter (≥3h) +
fragment-classify by start window + ask the user.

## Discriminator-table method
Build a table of signature rows × candidate hypotheses, gradable SUPPORTS / WEAK
/ CONTRADICTS / neutral. Cover:
- gradual-vs-stepped shape (firmware usually steps; a *smooth* decline does NOT
  clear restage — re-normalization can be gradual; check the sh_ver ledger,
  absence is WEAK not fatal).
- selective metric (deep ↓ with light flat favors relabel/restage; misalignment
  redistributes deep→light/wake; a relabel shows light RISING at flat total).
- flat efficiency/latency/fragmentation (favors algorithm-side; load usually
  shows latency/fragmentation changes).
- HRV/RMSSD + RHR same-window (load signal; night-after-new-modality ≈ rest
  nights kills the ACUTE-load version, but chronic-load onset still counts —
  check whether the decay start-week coincides with a new modality: Aug 2026
  decay began W30, exactly the BodyCombat start week).
- **inversion check** — only on VERIFIED series. "Deep peaked at the LATEST
  bedtime" was itself an artifact of the fabricated bedtime series; the paradox
  dissolved when the x-axis was corrected. An inversion argument is worth
  exactly as much as its axis.

## Action-uncertainty rule (corrected)
Don't revert a behavior on a thin competing hypothesis — but FIRST verify the
lever exists. The "validated earlier-bedtime lever" run-008 protected was itself
derived from the fabricated series; REV A voided it (no advance ever happened →
no lever; the Oct trial was CANCELLED, not held). Levers, like fingerprints,
must survive Gate Zero before they are protected or reverted.

## Verdict vocabulary + schedule pattern (corrected)
- Probability rankings with confidence bounds ONLY when the load-bearing
  fingerprints verified. When fingerprints void: **co-lead hypotheses with NO
  percentages** (pretended precision on fabricated inputs is worse than none).
- Deliver a pre-registered dated schedule with named falsifiers, keeping only
  verified discriminators: Sep 13 restage byte-diff (capture sh_ver NOW), Sep 27
  deload verdict (a 2-week load cap IS the C-test). A trial whose premise died
  is REMOVED from the schedule.
- Rules that survive: at most ONE lever moves at a time; "do nothing" is the
  default while the leading hypothesis resolves for free; explicit DO-NOT list
  matters as much as the DO list (don't medicate a possible artifact, don't
  react to single nights — weekly medians only, don't quit the new modality on
  unproven attribution).
- Record the root cause in the runbook: a deliberation is only as good as its
  input series; the panel's convergence was real agreement about fabricated
  data.

## Physiological grounding (use AFTER Gate Zero)
- SWS dominates the first cycles (homeostatic Process S) and is fairly
  phase-robust in forced-desynchrony studies; earlier bedtime at constant wake
  trims homeostatic drive slightly — it does not halve deep.
- A ~7h constant duration + flat efficiency/latency in the face of a 30-min deep
  drop is architecturally inconsistent with behavioral stress.
- These arguments killed the naive bedtime story in run-006 — but post-REV A
  they are supporting evidence only; the case-killer was Gate Zero, not theory.
