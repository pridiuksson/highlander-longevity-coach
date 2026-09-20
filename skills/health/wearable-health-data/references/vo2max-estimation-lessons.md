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
only −0.8; ±5 = ±0.55; prior sd 2.5 = ±0.28. The whole
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

Tanaka age-predicted HRmax (179.3 at age 41) is off by 26 against seven
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
**2026-09-20: harvester is v3.2** — adds a fallback rescuing up to 4 central
180 s windows (CV_SPEED ≤ 0.06, CV_HR ≤ 0.06 per window) for runs with ZERO
primary segments; the primary greedy path is byte-identical to v2.2 (38
insertions, 0 deletions; the original segments reproduce exactly). The
fallback exists because long continuous efforts (HR drift over a 25-min tempo)
fail a whole-segment CV_HR ≤ 0.05 flatness gate and silently produce zero
segments — the most fitness-relevant sessions never entered the fit.

## 6. Memos are hypotheses, never Source of Truth (2026-09-20, user-mandated rule)

A prior memo's prose claim about economy-bias direction was found to be
directionally WRONG — caught only when re-derived from raw data. The correct
statement, verified by simulation on the real segment cloud (OLS is linear in y,
so the ratio is exact): if the subject's economy is k% better than the ACSM
population average, the same machinery run on true VO2 returns k% LESS — the
raw ACSM-based estimate OVERSTATES truth by ~k% of the point. The economy
*correction* moves the number down; the *uncorrected bias* pushes the estimate
UP. Rule: before relying on ANY prose claim from a prior memo, re-derive it
from raw data with tools; stale memos get corrected in the live doc, never
trusted. (A user challenge — "did you look hard enough?" — is a prompt to
re-derive, not to re-defend.)

## 7. Era-pooling is a lagging estimate, not a "conservative floor" (run-015)

Pooling segments across years mixes real improvement arcs into the fitted line:
an earlier-era cloud that looks "degenerate" (negative cross-sectional slope) is
often REAL physiology — within-year fitness arcs show up as era-mixing, not
junk data (verify with monthly/period mean HR/speed before discarding; note
within-run slopes need ≥3 segments per run, which sparse earlier eras often
lack). Pooling drags the intercept toward history: in the verified case the
era-split point exceeded the pooled point by 1.83 ± 0.28 units across
bootstrap seeds (every seed > the pre-registered ±1.0 adoption threshold).
Do NOT call the pooled number a "conservative floor" or "bound" — Simpson-type
direction is not guaranteed. Before any TREND-slope claim ships, run a
random-run-intercept mixed model (segments within runs within eras); cluster
bootstrap by date is only a partial fix for within-run correlation. Point
estimates are unaffected. **The gate was run (2026-09-20)**: the within-run
(intercept-removed) slope proved statistically zero (cluster-robust CI crossing
0; n=21 runs) because within-run segments span only ±5% speed — the
cross-sectional fitted slope is a BETWEEN-run/era regression, and trend claims
must come from matched-speed/pace comparisons, never from the fitted slope.

## 8. Segment granularity defines method admissibility (R2 gate, run-015)

CV-gated steady-segment methods make per-window speed MANDATORY. Health-Connect
has NO speed channel for any run (verified from the FOSS webhook app's source:
zero `speed` code paths; exercise records carry only type/times/duration, with
steps/avg_cadence on some records) — 1 Hz HR IS present in HC during runs (a
lower sample-rate impression can be a miscount of a different record set). A
flat mean-speed profile reconstructed from the session total would trivially
pass any CV gate — fabricating exactly the steadiness the pipeline measures.
Therefore: per-run pace analysis stays export-sidecar-only; a fresh vendor
export is the unblock for any gap period; gap-period runs enter only as
whole-run (mean-speed, mean-HR) matched-pace covariates until then. Simulation
gate before building ANY new segment class: degrade a sidecar'd run to the new
granularity and test the real gates — if rejection ≥ 50%, kill the class.
