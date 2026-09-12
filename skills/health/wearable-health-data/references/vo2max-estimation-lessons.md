# VO2max estimation — method-level lessons (verified 2026-08-29/30, this pipeline)

Context: anchored estimate 48.9 [42.5–55.2] @ HRmax prior N(205.5, 2.5) from 112
steady-state 1 Hz segments / 79 runs, ACSM demand + individual HR→VO2 line
(fitted: VO2 = 26.18 + 0.1108·HR), cluster bootstrap over runs, ±5% economy term.
Full memo with citations: `health.health_dir/samsung-data/VO2MAX_MEMO.md`;
runbook finding 10. These are the transferable method lessons, not the number.

## 1. Sensitivity-analyze a contested anchor BEFORE debating it

When a prior (HRmax 205±2.5) is questioned ("is it really 205, or declining to
198?"), compute d(estimate)/d(prior) first. Here the estimate IS the fitted line
evaluated at HRmax, so sensitivity is linear and tiny: shifting HRmax across the contested range moves the estimate
only −0.8; ±<YOUR_RESTING_HR_BPM> = ±0.55; prior sd 2.5 = ±0.28. The whole
"HRmax completeness" debate was empirically inert — CI width is dominated by
slope (r=0.31; +38% slope → +2.1) and economy bounds (→ +8.1). Kill weak
controversies with arithmetic before spending subagents on them.

## 2. Validate a fitted model on its most extreme fresh point

The single best out-of-sample test: take the hardest measured event AFTER the
fit (hill rep 4: mean HR 184, the day's maximal effort) and check it against the
line — fitted 46.6 (95.3% of the anchored estimate), independently ACSM
flat-ground cost at the rep's actual speed = 46.9. The maximal point sits ON the
calibrated line. One extreme-point validation beats several random spot checks;
and the max is where linearity assumptions are most at risk, so passing there is
strong evidence.

## 3. Convergent-evidence stack for a single-subject estimate

Rank estimates from independent method families and use disagreement as
information: anchored pipeline 48.9 | watch scalar 47.78 (quarantined *series*,
but a single scalar landing inside the CI corroborates) | Daniels VDOT floor
46.6 from training paces | Uth HR-ratio method 70–79 (EXCLUDED for cause —
HRmax/HRrest leverage explodes at RHR 38.6, "envelope only"). A method that
disagrees wildly at the subject's physiology is not evidence — quarantine it
with the mechanism named, keep it only as a sanity envelope.

## 4. Formula-vs-data precedent

Tanaka age-predicted HRmax (179.3 at age 41) is off by <YOUR_RESTING_HR_BPM> against seven
sidecar-verified maximal plateaus (195–205, each cross-checked summary ≡ 1 Hz
sidecar). Population formulas are priors of last resort for an instrumented
subject — the individual's own measured ceiling outranks any age equation.
Related: the WATCH's own internal HRmax ladder (repeated revisions) was the root
of the quarantined VO2max slide — device re-anchoring artifacts, not
physiology (runbook finding 2).

## 5. When re-running after prior changes

`vo2max_est.py` (v2.3): prior N(205.5, 2.5) floor 195; `build_vo2max_dataset.py`
v2.2 (seconds-weighted segments, length gated in seconds, speed floor 150
samples). Rebuild chain steps in runbook §Rebuild. Independent checkers:
`checker_vo2max*.py` — all claims byte-reproduced 2026-08-29.
