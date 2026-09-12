# Parsing workouts from Samsung Health app screenshots

Built 2026-08-30 (hill-run n=2, Aug 23 vs Aug 30, validated across 3 screenshots
× 2 passes each, zero label disagreements). Trigger: user shares phone
screenshots of a Samsung Health workout — chart screens (HR/pace, Tempo/Höjning/
Takt) and/or the Träningsdetaljer (details) screen — to extract while awaiting
the raw export. User-prescribed process, verbatim: "same process as before:
**ocr, vision, cross-match**".

## The process

1. **Vision pass (chart interpretation).** Full domain context allowed: curve
   shapes, spike counts, alignment between overlaid series, axis ranges,
   time ticks, finish flag.
2. **OCR pass (transcription, interpretation banned).** Second vision_analyze
   call framed as "transcribe every label/value exactly, no interpretation".
   The two passes must AGREE on every label and value; any disagreement =
   pixel ambiguity → record UNRESOLVED, never average.
3. **Cross-match, three layers:**
   - **Internal consistency (details screen):** avg pace × distance = duration;
     steps ÷ duration = avg cadence; max pace ⇄ max speed reciprocal
     (03'23"/km = 17,7 km/h ≈ "17,6"); elevation gain vs lowest/highest altitude.
   - **Cross-screen:** chart axis ranges must bracket the summary values;
     chart time ticks + finish flag vs Träningstid/Total tid.
   - **Cross-session:** compare against the prior validated run doc
     (`RUN_*.md`) and known device baselines — this is what makes n=2 claims.

## Priority: the summary screen ARBITRATES chart pixels

Chart pixel reads carry tolerances: peaks ±3–<YOUR_RESTING_HR_BPM>, troughs ±5–10, rep
boundaries ±20 s. Details-screen numbers are exact and win every conflict.

**Incident that set the rule (2026-08-30):** chart crests read "~175–185,
nothing reaches 198" → the details screen showed **Max puls 196**. Sustained
crests ≠ max; brief excursions hide at chart resolution. Never publish a
"max X" or "nothing reached Y" claim from chart pixels when a details screen
exists — request the details screen first, or gate the claim as pixel-grade.
Corrections of your own earlier pixel reads go in the reply prominently
("the correction that matters"), not buried.

## Structure counts: testimony > gain-math > pixel spikes

- Elevation-gain ÷ climb-height UNDER-COUNTS reps (barometric noise merges
  short climbs: 115 m ÷ 24 m ≈ 5 vs actual 7).
- Pixel spike counts OVER-COUNT (side-transitions/undulations read as reps:
  9 tall spikes vs actual 7 climbs).
- Ask the user the structure directly (rep count, sides/route) — answers are
  fast and decisive. Then reconcile: pixel spikes − transition artifacts =
  testimony climb count.

## Venue pairing (ask explicitly)

"Last week it was the same hill" (testimony) turned two sessions into a
CONTROLLED experiment: hill constant (elevation band 8–32 vs 14–40 m
independently agreed), 7 days apart → format is the only variable, and the
+8 avg-HR delta became attributable to format, not fitness. Elevation bands
only SUGGEST venue identity; the user's one-liner CONFIRMS it. Always ask
"same venue?" before attributing deltas in paired-session comparisons.

## Conditions + intent questions (with every parse)

Conditions (rain? surface wet? air stuffy?) and intent (deliberate format vs
improvised) modify interpretation: stuffy air inflates HR at a given pace; a
wet surface caps downhill float pace and is a safety flag, not a fitness
signal. End the reply with a short numbered ask-list; the user answers
selectively and each answer upgrades the record (sidecar export, max-HR
field, total elevation gain, intent, RPE).

## Swedish label vocabulary (Träningsdetaljer)

Träningstid / Total tid (moving / total time) · Distans · Kalorier · Steg ·
Tempo medel/max (pace, mm'ss"/km) · Hastighet medel/max (km/h) · Höjning
(Höjdförändring / Lägsta / Högsta höjning = gain / low / high) · Lutning
(Total stigning / Total sluttn. = ascent / descent distance) · Puls snitt/Max ·
Takt medel/max (st./m = cadence steps/min) · VO2-max. Formats: decimal
COMMAS, pace as 03'23", thousands with thin space (5 051).

## What screenshots cannot give (sidecar checklist stays open)

Rep-level HR peaks, launch HRs after floats, +30 s recovery checkpoints,
excursion durations (artifact-vs-real on a max-HR spike), true rep boundaries.
Keep a "Pending sidecar" checklist in the run doc; run the full rep table when
the export lands (`references/exercise-sidecar-channels.md`).

## Documentation shape (validated template)

`RUN_YYYY-MM-DD_TYPE.md`: session-summary table WITH a consistency-check
column · structure section (testimony + charts, disagreements recorded) ·
n=2 comparison table · interpretation that explicitly corrects earlier pixel
reads · pending-sidecar checklist · cross-refs. Plus a one-line entry in
<YOUR_BASELINE_DOC>.md's training block. Conventional commit on the current PR branch
(2026-08-30: `df99627`, `2b20604`).
