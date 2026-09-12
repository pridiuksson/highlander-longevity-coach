# Timestamp-frame discrimination — worked case (Garmin sleep strings, 2026-08-16)

Class problem: a raw timestamp column in a vendor export is labeled GMT/UTC. Is it
really UTC, or local-display time mislabeled? A decade bedtime-trend chart depended on
it and the answer flipped THREE times in one day before a mechanical protocol settled
it. This file records the protocol, the anchors, the circular proof that fooled two
readings, and the peer-review loop that caught it.

## The failure sequence (why "plausibility" lost three times)

1. Reading 1 (field-name trust): `sleepStartTimestampGMT` → assumed UTC. Correct by
   luck, unproven by method.
2. Reading 2 (continuity/plausibility): final-era strings flowed "seamlessly" into the
   next device's local-labeled times → concluded LOCAL. Wrong: the "seamless" join was
   against an IMPORT-COPY (below), and the distributions it leaned on were compatible
   with both frames.
3. Reading 3 (retraction on circular evidence): the parser for the OTHER device was
   discovered inverted that same morning; its "local" columns were used as the
   reference to "prove" this device's frame. Both sides of the comparison were
   unverified — UTC-to-UTC agreement misread as local-to-local.

## The five mechanical anchors (settle frames ONLY with these)

| # | Anchor | Result in worked case |
|---|---|---|
| a | **Epoch millis in sidecars** — absolute instants immune to labeling | Samsung side proven: `.liv`/`sleep_status` JSON epochs == CSV strings to the second |
| b | **Same-instant multi-device overlap** — two sensors on one sleeper during a handoff week | Night in the 2021-08 handoff week: Garmin 21:42 vs Samsung-native 22:18 both-as-UTC = 36 min apart (two algorithms, one sleeper). Local reading: Garmin detects sleep 3h36m BEFORE the other wrist — impossible |
| c | **User testimony** — known wake/event times | UTC reading → wakes 06:45–07:45 local ≈ user's reported ~06:40–08:00. Local reading → 04:00 wakes, contradicted |
| d | **Downstream-impossibility** — compute a physical invariant under each hypothesis | Sleep-end → first-workout gap, n=228: UTC reading median **+1.48h** (min +0.40); local reading median **NEGATIVE** (workouts logged before sleep ended) for dozens of nights |
| e | **DST seasonal-median** — sharpest, DST regions only | Winter-vs-summer medians of the RAW string column: UTC strings predict ~±1h seasonal shift (fixed local schedule, moving offset); local strings predict ~0h. Measured **+1.13h** (summer wake-strings 06:16 / winter 07:23; n=361/346) |

Notes on (e): use CLEAN months (Dec/Jan/Feb vs Jun/Jul/Aug) to avoid DST-boundary
nights; use the wake (end) column, less lifestyle-mobile than bedtime; also immune to
the "device clock itself ran UTC" edge case (functionally identical to the UTC reading).

## The circular proof to watch for

A minute-identical record in both stores (source export + importer's DB) was cited as
"the importer stores it in its UTC column, therefore the source is UTC." Peer review
flagged it: **a verbatim copy proves the importer ASSUMED UTC, not that the source
emitted UTC.** Any cross-source agreement routed through a sync/import path inherits
the importer's assumption. Genuinely independent sensors only (anchor b).

## Non-decisive tests: publish them as negatives

- RHR-in-window containment (resting-HR samples falling inside sleep windows under each
  frame): 13.2% (UTC) vs 10.0% (local) — right direction, mushy because sampling is
  all-day. Recorded as non-decisive, NOT cited as support. Publishing weak negatives is
  half the value of the protocol: the next auditor knows what was tried.

## The peer-review loop for contested empirical conclusions

1. Re-derive every anchor from primary data in-session (raw rows, raw bytes) — this
   alone caught a stale number (+0.7h/n=218 quoted from memory; fresh per-night
   pairing gave +1.48h/n=228).
2. Hand the peer RAW DATA + inference chain + conclusion under test (not your summary).
3. Demand: alternative hypotheses, weakest anchor, circularity audit, explicit
   "would you flip on this evidence?" verdict.
4. Execute the peer's demanded mitigation — its missing line is often the strongest
   test you haven't run (here: it wanted an independent epoch check; the DST test
   delivered the same independence another way).
5. When a published number has flipped twice: FREEZE the artifact, name the missing
   discriminator explicitly, resolve it, and only then regenerate. Never flip a third
   time on re-weighted old evidence — only on a NEW mechanical anchor.

## Resolution

Garmin `sleepStart/EndTimestampGMT` = TRUE UTC. Local = stored +2h winter/+3h summer
(Vilnius EET/EEST era). Decade bedtimes: Garmin era drifted later,
Samsung era earlier — the ~1.5h lifestyle change is real. Evidence scripts:
`health.health_dir/decade-sleep/tz_dst_discriminator.py`, `tz_overlap_anchors.py`,
`tz_probe.py`; full saga in `health.health_dir/garmin-verified-data.md` §tz and
`health.health_dir/decade-sleep/README.md` correction history items 5a–e.
