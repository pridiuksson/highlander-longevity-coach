# VO2max estimation — method-level lessons (verified 2026-08-29/30, one pipeline)

These are the transferable method lessons, not the numbers. Every number below is one of
two kinds, and applying this file to your own subject means knowing which you are reading:

- **Parameters** — gates, thresholds and window lengths the method applies. Take these
  verbatim; they ARE the method.
- **Observations** — what one subject's data did, kept as the receipt for a lesson and
  tagged inline `(receipt: …)`. They are NOT norms, targets or expectations. Do not size
  a gate, a filter or an adoption threshold from them, and never quote one as a property
  of a method ("formula X is off by N") — it is a property of this dataset.

Source observation set, for the receipts only — not a template: anchored estimate 48.9
[42.5–55.2] @ HRmax prior N(205.5, 2.5) from 112 steady-state 1 Hz segments / 79 runs,
ACSM demand + individual HR→VO2 line (fitted: VO2 = 26.18 + 0.1108·HR), cluster
bootstrap over runs, ±5% economy term. Full memo with citations:
`health.health_dir/samsung-data/VO2MAX_MEMO.md`; runbook finding 10.

## 1. Sensitivity-analyze a contested anchor BEFORE debating it

When a prior is questioned ("is it really 205, or declining to 198?"), compute
d(estimate)/d(prior) FIRST — before debating it, and before spending subagents on it. When
the estimate IS the fitted line evaluated at the prior, sensitivity is linear, so this is
arithmetic rather than work. **Run it on your own prior: the step is transferable, the
conclusion is not.** For this subject the whole "HRmax completeness" debate was
empirically inert — movement well inside a CI dominated by slope and economy bounds
(receipt: HRmax 205±2.5, contested range to 198 → −0.8; ±5 → ±0.55; prior sd 2.5 →
±0.28; slope r=0.31, +38% → +2.1; economy bounds → +8.1). Yours may not be, and you
cannot know without computing it. Kill weak controversies with arithmetic.

## 2. Validate a fitted model on its most extreme fresh point

The single best out-of-sample test: take the hardest measured event AFTER the
fit and check it against the line — predict it before you look at it. One
extreme-point validation beats several random spot checks, and the max is where
linearity assumptions are most at risk, so passing there is strong evidence. Pick
YOUR hardest post-fit event; this subject's was a maximal hill rep, which landed
on the calibrated line (receipt: mean HR 184, fitted 46.6 = 95.3% of the anchored
estimate, against an independent ACSM flat-ground cost of 46.9 at the rep's actual
speed).

## 3. Convergent-evidence stack for a single-subject estimate

Rank estimates from independent method families and use disagreement as
information: a family landing inside the other's CI corroborates even when its
own series is quarantined. A method that disagrees wildly AT YOUR SUBJECT'S
physiology is not evidence — quarantine it with the mechanism named and keep it
only as a sanity envelope. **The mechanism is the finding, not the method's
name:** this subject's HR-ratio method was excluded because its HRmax/HRrest
leverage explodes at a very low resting HR — a property of that physiology, not a
verdict on the method. Do not carry the exclusion over to another subject.
Receipts for the worked stack: anchored pipeline 48.9 | watch scalar 47.78 |
Daniels VDOT floor 46.6 | HR-ratio method 70–79, excluded for cause at RHR 38.6.

## 4. Formula-vs-data precedent

Population formulas are priors of last resort for an instrumented subject — an
individual's own measured ceiling outranks any age equation. **Do not quote the
size of a formula's miss as a property of the formula:** it is subject- and
age-specific, and the transferable claim is the ranking, not the margin. Receipt
for this subject at age 41: an age-predicted HRmax sat well below seven
sidecar-verified maximal plateaus, each cross-checked against its 1 Hz sidecar.
Related: a device's own internal HRmax ladder (repeated revisions) can be the
root of a quarantined VO2max slide — re-anchoring artifacts, not physiology
(runbook finding 2).

## 5. A flatness gate silently drops the sessions that matter most

A whole-segment flatness gate (CV of speed and HR within a segment) keeps the
segments comparable, and it can also reject every segment of your hardest
session: long continuous efforts drift over their length, so a hard tempo run
fails a whole-segment CV_HR ≤ 0.05 gate and yields ZERO segments — silently, so
the most fitness-relevant sessions never enter the fit and nothing errors. Two
transferable lessons: count segments per session before trusting a fit built on
them, and fix the gate with a fallback that rescues the central windows of an
otherwise-rejected run under per-window caps (180 s windows, CV_SPEED ≤ 0.06,
CV_HR ≤ 0.06) — then verify the primary path still reproduces its previous
segments byte-for-byte, so the fallback cannot move existing results.

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
lack). Pooling drags the intercept toward history. Do NOT call the pooled number
a "conservative floor" or "bound" — Simpson-type direction is not guaranteed.
**Pre-register the adoption threshold** before comparing the two points: the
threshold is the parameter (a ±1.0-unit margin was adopted here) and it is what
makes the comparison a test rather than a story. The observed gap is the receipt
— an era-split point exceeding the pooled point by 1.83 ± 0.28 units across
bootstrap seeds — and its size is not an expected effect for anyone else.
Before any TREND-slope claim ships, run a random-run-intercept mixed model
(segments within runs within eras); cluster bootstrap by date is only a partial
fix for within-run correlation. Point estimates are unaffected. **Check the
within-run slope before trusting a fitted trend slope:** with the run intercept
removed it is typically statistically zero (cluster-robust CI crossing 0) because
within-run segments span only a narrow speed range — ±5% here, a general hazard
rather than a quirk of this dataset. The cross-sectional fitted slope is then a
BETWEEN-run/era regression, and trend claims must come from matched-speed/pace
comparisons, never from the fitted slope.

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
