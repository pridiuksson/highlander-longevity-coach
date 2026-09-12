# Cross-source "corroboration", rebuild-from-raw, and gate-instrument traps

Session that produced this: 2026-08-16, decade sleep-patterns + Garmin/Samsung
cross-match audit. These sit alongside `sleep-bedtime-extraction-audit.md` and
`lineage-dual-night-key.md` — different failure classes, same domain.

## 1. Two "devices" holding byte-identical data = ONE measurement, not corroboration

The single most dangerous pattern for cross-device analysis: you pull the SAME metric
from two supposedly-independent sources, see agreement, and call it cross-validation.
It is often the same record ingested twice.

Worked case: Samsung-era sleep and Garmin-era sleep overlapped at the device handoff
(2021). The runbook claimed "both devices on night-table during transition week;
±2h window-interpretation difference between algorithms." Re-derivation showed the
Samsung 2021-08-25 night and the Garmin 2021-08-26 row were **identical to the minute**:
window 23:<value>→<value>:17, deep 184 min, light 217 min, wake 8 min. Samsung Health had imported
the Garmin record from Garmin Connect on switch day. The "±2h difference" was a
timezone misread: someone compared the session's `start_utc` (21:28) against its own
`start_local` (23:28). There was never a second device.

Rules:
- **Before calling cross-source agreement "corroboration," match BY CONTENT, not by
  provenance.** Are the metric VALUES (durations, per-stage minutes, window edges)
  identical to the minute / to the last discrete unit? Byte-identical values on two
  supposedly-independent sensors is *more* suspicious than a close-but-not-equal match.
- **Check the direction of ingestion.** A handoff-night record appearing in both stores
  with identical values is almost always a sync/import path (app X pulled from app Y),
  not two sensors. Look for an export/import or "connected accounts" seam at the date.
- **The "±2h difference" that equals a timezone offset is a re-labeling, not a sensor
  difference.** If two window values differ by exactly a whole-hour timezone offset and
  the underlying durations are identical, you are comparing one instant under two labels.
- **Practical rule:** exclude/de-duplicate the imported record from the receiving
  source's native stats (e.g. drop the Samsung night that is really Garmin data).

## 2. "GMT"-named fields may carry LOCAL time — validate against an independent anchor

Consumer-device exchange formats name fields `*Gmt` / `*UTC` that are sometimes
actually local-display time. Never trust the column name.

Worked case: Garmin `sleepStartTimestampGMT` fields were proven to be *local display
time*, while that same export's workout `begin_gmt_ms` WERE genuine UTC (G11 gate,
begin_local_ms − begin_gmt_ms = +1h winter / +2h summer, DST-aware). The sleep fields
were not UTC. Reading them as UTC put every bedtime 2–3h late and inverted a decade
narrative (claimed 25:<value>→<value>:47 when truth was 22:<value>→<value>:11).

How to validate the semantic of a timestamp column:
- **Independent cross-source anchor:** the identical-content handoff night above pins the
  semantics — one field's value equal to the other source's *local* time (and its `-utc`
  equal to the other's *UTC*) tells you which labeling each column actually holds.
- **Continuity across a provenance boundary:** values that flow continuously through a
  device switch (Garmin last Aug-2021 week → Samsung-first-native week, ~30-40 min apart,
  same range 21:27–01:02) mean the column is local; a ±2-3h discontinuity would force
  absurd values (bedtimes at 2–4 AM).
- **DST offset between two ms fields in the SAME row** (e.g. `begin_local_ms` vs
  `begin_gmt_ms`) discriminates DST-aware vs fixed-offset labeling per device.

## 3. Provenance strata INSIDE one "source" — a trend may be a device shift

A single source era can itself be two regimes. Samsung "era" 2021-2026 split at
2022-10 (phone-staged sleep vs Galaxy-Watch-staged): deep 10%→<value>→<value>%, REM <value>→<value>→25%.
Part of the apparent "rising deep/REM" across 2021-2024 was provenance shift, not
physiology. Before reporting any trend that spans a device/adoption/handoff boundary,
confirm the metric is measured identically on both sides.

## 4. Rebuild-from-raw as the strongest reproducibility check

Auditing against the pre-built DB only proves your re-derivation of *that* artifact.
The decisive test is a **fresh rebuild from raw sources into a sandbox**, then full
byte-level table comparison vs the frozen reference:
- Freeze a reference: `sqlite3 source.backup('/tmp/ref.sqlite')`, md5 it.
- Sed-redirect ONLY the path constants in the parsers into `/tmp/rebuild/`, run them
  against the same raw zip/cache. Verify via `grep` that only the path line changed.
- Row-count AND full-row comparison per table (ORDER BY pk), not just counts — counts
  can match with corrupted content. Include ALL tables; do not assume bookkeeping
  (import_meta, fit_progress) carries timestamps — they may be pure data and comparable.

## 5. The gate/validator instrument itself needs adversarial coverage

A validator passing on a production DB is only meaningful if it HAS FAILED before. Encode
each historical bug class as a negative-control injection:
- If the regression that caught the original bugs (e.g. unit-scale ×100 on a
  FIT-arbitrated field) was only a *manual* spot check, make it a permanent `--negative-control`
  case so the instrument can independently prove it detects that corruption class.
- Check that every DETECTOR (gate class) is exercised by at least one injection. If the
  crown-jewel arbitration gate was never in the negative-control set, its green PASS is
  unvalidated. Add classes until every gate used in production has a corruption case.
- Run negative controls on the SANDBOX rebuild, not the production DB, so the corruption
  test never touches the real store.

## 6. Render verification without a vision model / browser

When you can't visually inspect a chart (no CDP browser, vision endpoint text-only):
- **Pixel-series check:** after rasterizing, verify each intended series' exact hex color
  appears within that series' band of the PNG (`set(im.getdata())` per band). Confirmed
  7/7 series in-correct-panel here, and caught a P3 curves-collapsed regression the first
  pass.
- **SVG polyline regex attribute-order trap:** `<polyline points="..." fill="none"
  stroke="...">` — `stroke` comes AFTER `points`. A regex requiring `stroke` before
  `points` silently finds 0 polylines and masquerades as "empty render." Match with
  `points="([^"]+)"[^>]*stroke="..."`.
- **Sampling band math:** compute panel bands from the ACTUAL y-coordinates the generator
  used, not guesstimated fractions — sampling wrong fractions produced a false
  "P3 empty" on the first check (the band straddled a panel gap).
- **Denominator artifact:** plotting stage SHARES over a conditional denominator (share of
  staged-only nights) can collapse curves to one constant row when most months have the
  same staged share; prefer ABSOLUTE per-night metrics (minutes) which separate cleanly.

## 7. Tool runnability is a claim to verify

A prior session may report "ran every script verbatim." Verify it: actually execute the
committed script. Here two cross-source tools crashed as committed (sqlite `ATTACH
DATABASE 'file:...?mode=ro&immutable=1'` requires the MAIN connection opened with
`uri=True` — the main connect must also be a `file:...?mode=ro` URI). Both tools' numbers
were later reproduced by independent SQL (their data was right), but the committed
scripts were not runnable — contradicting the verbatim-run claim. Never inherit a prior
"tool X runs" claim; re-run the artifact.
