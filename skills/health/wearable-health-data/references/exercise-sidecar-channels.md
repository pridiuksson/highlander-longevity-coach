# Exercise sidecar channel map + rep extraction (verified 2026-08-29, GW7 2026-08 export)

For hand-processing a specific workout (rep splits, HR/speed/altitude series).
Cost of learning: 6 failed probes in one session — this map is the shortcut.

## File layout (per workout datauuid, under the export's dated directory)

`Samsung Health/samsunghealth_<account>_<stamp>/jsons/com.samsung.shealth.exercise/<0|hex>/<uuid>.<NAME>.json`

| NAME file | Contents |
|---|---|
| `com.samsung.health.exercise.live_data.json` | **STRUCTURE ONLY** — 4,021 rows of `{start_time, elapsed_time, interval, segment}` with NO data channels. Do not mine it for values. |
| `com.samsung.health.exercise.live_data.json` — same name, OTHER naming generation: `com.samsung.shealth.exercise.live_data_internal.json` | internal copy, also structure-only in this export |
| `com.samsung.health.exercise.location_data.json` | `{latitude, longitude, altitude, accuracy, start_time}` (GPS 1 Hz) |
| `...live_data.json` (combined channel payload — VERIFY per export) | HR/speed/cadence/calorie/distance channels may live in the combined file OR split per channel. Introspect before assuming: list the union of element keys. |
| `<uuid>.sensing_status.json` / `.heart_rate.json` | per-channel metadata (`is_valid`, sampling_rate, max_hr_auto) — the `heart_rate.json` chart_data is the recovery-curve family, NOT the in-workout stream. |

**Naming-generation trap:** older exports use `com.samsung.shealth.*.live_data_internal.json`
(s-health prefix); newer use `com.samsung.health.*` prefix. Both may exist for the same
workout. Match on the datauuid + substring (`live_data`, `location_data`), then introspect
element keys — never hardcode a full filename (export paths carry per-export timestamps).

## Timestamps

- Element `start_time` is **epoch milliseconds** (UTC). Convert:
  `datetime.fromtimestamp(ms/1000, tz=timezone.utc)`; local display = manual offset or DB join.
- `elapsed_time` is ms since workout start — usable for rep windows if you know the
  workout start epoch (= first element's start_time − first elapsed_time).

## Rep-extraction recipe (hill session 048d9b04, worked example)

1. Identify rep windows from the HR stream (smoothed bout detection against a fixed bpm
   threshold) — NOT from fixed clock windows: smoothed-HR bouts and wall-clock windows
   differ by 15–60 s and mixing them produces mismatched speed/HR pairs.
2. Per window, aggregate each channel independently (`heart_rate` from the HR channel,
   `speed` from speed channel, `altitude` from location stream — they are separate arrays
   keyed only by start_time).
3. Per-rep altitude delta from GPS is NOISE at 60–90 s scale (rep4 read ±2 m over a real
   ~10–15 m climb). Use workout-total altitude_gain or derive grade from the demand model
   instead; never per-rep GPS altitude.
4. Cross-check maximal events against the workout summary row (`max_hr` ≡ sidecar max
   held on the 198-bpm rep) — two independent surfaces agreeing is the artifact filter.

## Parsed hand-analysis exemplar

`health.health_dir/samsung-data/RUN_2026-08-23_HILL.md` — rep table, 198-bpm event
arbitration, HRmax re-anchoring table (7 maximal efforts), recovery-night section.
