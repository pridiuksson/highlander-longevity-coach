# Samsung AGEs Index — metric research (verified 2026-08-29)

What `com.samsung.health.advanced_glycation_endproduct` (+ `.raw`) actually is, per
public sources. Read BEFORE re-researching the metric. Export-schema observations
(boundaries array, raw-window fields) have **no official documentation** — Samsung
publishes nothing about these fields.

## Datatypes in the export
- `advanced_glycation_endproduct`: daily index ~0–750; observed `level_boundary`
  [158, 354, 390, 586, 728] (5 bands); `percent` field mostly 47–53 (semantics unknown).
- `.raw`: nightly measurement windows 01:00–05:00; `binning_data` JSONs carry
  `{timestamp, score, feature:[7 ints]}` where `feature[6]` ≈ 200,000 — undocumented (UNVERIFIED).

## What Samsung officially says (CONFIRMED-SOURCE)
- "Indicator of metabolic health and biological aging strongly influenced by overall
  lifestyle and dietary habits"; measured with the redesigned BioActive sensor during
  sleep; Galaxy Watch7+ only; Samsung Health ≥6.27, Android 10+.
  - https://news.samsung.com/global/unlocking-new-possibilities-for-preventative-wellness-with-new-galaxy-watch-and-bioactive-sensor
  - https://www.samsung.com/us/apps/samsung-health/ — footnote 17: "Not intended for use
    in detection, diagnosis, treatment of any medical condition. AGEs index is for your
    personal reference only."

## How it's measured (PLAUSIBLE-MULTI-SOURCE — optical, not HRV/pulse-wave)
- New BioActive sensor added Violet + **Ultraviolet LEDs** explicitly enabling the
  feature (newsroom, above).
- Likely skin **autofluorescence** (same technique as Cavero-Redondo 2018
  meta-analysis); accuracy of Samsung's interpretation "unknown" —
  https://www.wareable.com/features/samsung-galaxy-watch-ages-index-explained
- APK teardown names **Diagnoptics** (maker of the clinical AGE Reader
  autofluorescence device) as partner; AGEs' "characteristic fluorescence" enables
  non-invasive optical read —
  https://www.androidauthority.com/samsung-galaxy-watch-ages-index-apk-teardown-3456073/
- No public source derives it from HRV or pulse-wave signals.

## Bands / levels (UNVERIFIED numerics)
- No official doc publishes the 0–750 range or thresholds; Samsung Health Data SDK
  data-types page has no AGEs entry
  (https://developer.samsung.com/health/data/guide/features/data-types.html).
- App UI: 5 color zones; community mapping: green = "Adequate", yellow = "High"
  (reddit.com/r/GalaxyWatch/comments/1kt47qf); 393 sat mid-scale; same 393 shown in
  different bands on watch vs phone (reddit.com/r/GalaxyWatch/comments/1kuyg2e).
  The export's boundaries array is the best numeric map available.
- Lower = better is implied, never stated in-app.

## Validation status
- Claims: biological age, metabolic health, age-group comparison. Diabetes/heart/
  stroke risk framing comes from partner Diagnoptics copy, not Samsung.
- **No published peer-reviewed validation of the watch index found** (Google Scholar
  + PMC, 2026-08-29). Officially "fitness and wellness only" (newsroom footnote 4).

## Confounders & criticism (PLAUSIBLE-MULTI-SOURCE)
- Experimental "Labs" feature; Wareable documented near-identical readings across
  most users.
- User-reported skin-fluorescence confounders: coffee intake
  (reddit.com/r/GalaxyWatch/comments/1eb3l8k); clean/dry skin + snug fit per Samsung
  Community (eu.community.samsung.com/t5/samsung-lounge/...td-p/14132957).
- Medication-linked band shifts (calcium beta-blocker / BP meds, reddit 1kuyg2e).
- Algorithm changed ≥once (~2025 UI update added numbers, re-banded users).
- Dietary AGEs form under high-temperature dry-heat cooking (grill/fry/toast);
  steaming + low-sugar diets reduce them (Twarda-Clapa 2022, Prasad 2017 — via
  Wareable). Pescatarian-specific data: none found (UNVERIFIED).

## Community data points (PLAUSIBLE-MULTI-SOURCE)
- Numeric reports: 393; 397 @ age 39 (orange); "almost all screenshots I see are in
  the orange" (reddit.com/r/GalaxyWatch/comments/1lfzq2o, /comments/1lvs23z).
  Pre-2025 unlabeled ~0–10 UI: most users 7–8/10 (Wareable).
- Score moves slowly; no credible day-to-day diet/sleep/exercise coupling reported.

## Reddit access note (2026-08-29)
Direct routes all die server-side (old.reddit JSON → "Blocked", pullpush →
Cloudflare, r.jina.ai anonymous → 403, browser daemon down). The route that worked:
**site-restricted web_search** (`site:reddit.com GalaxyWatch AGEs ...`) — Brave
snippets carry verbatim comment text.

## Pipeline implication
Treat as a consumer-wellness trend signal, not clinical: analyze rolling 30–90d
means, expect firmware/algorithm re-banding (see "Firmware re-scoring checks" in
SKILL.md), and never diff daily values across an algorithm-version boundary.
