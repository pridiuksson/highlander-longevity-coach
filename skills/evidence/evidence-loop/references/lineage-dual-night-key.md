# Worked case: dual night-key lineages manufactured a doc-internal inconsistency

Session: PR #6 audit (Samsung-side pre-draw D2 control numbers), repo `highlander-longevity-coach`,
`<YOUR_HEALTH_DIR>/samsung-data/`. Two PR#5-era tools computed "9-week pre-draw window" stats:
`predraw_windows.py` and `seasonal_control.py`.

## The two lineages

Both claimed "night-key = start_local − 18h", but implemented it differently:

- `predraw_windows.py`: `substr(datetime(substr(s.start_local,1,19), '-18 hours'),1,10)`
  → full-timestamp −18h. A sleep starting 22:18 on day D keeps key D (22:18−18h = D 04:18).
- `seasonal_control.py`: `date(substr(s.start_local,1,10),'-18 hours')`
  → date-only −18h, treated as midnight. date(D) −18h = D−1 **always**. Every night's key
  shifted one day earlier vs predraw.

`sleep_session.start_local` carried milliseconds (`'2025-07-02 22:18:00.000'`), so both
`substr(...,1,19)` and date-only are well-formed; the divergence is purely the date-vs-
datetime choice, not malformed strings.

## What it did to the numbers

| Lineage | D2 2025 deep med (9wk) | 2024 ctrl deep med | total min/wk (any) |
|---|---|---|---|
| predraw (datetime−18h) | **72** (n=61) | 60 (n=59) | identical 530/639/797 |
| seasonal date−18h (producing tool) | **73** (n=58) | **63** (n=56) | identical |

- Training total min/wk is lineage-*free* (raw `substr(start_local,1,10)` window) — clean
  MATCHes: D2 <value>→<value>, 2024 <value>→<value>, D1 <value>→<value>, hard-days <value>→<value>, RMSSD <value>→<value>.
- The deep medians are lineage-*sensitive*. The findings doc cited D2 deep as **72**
  (summary table) AND **73** (reference table + retraction text) — both "right", each under
  a different tool. The 2024 control deep **63** reproduced ONLY under the producing tool's
  (seasonal) lineage; re-derived under the documented/predraw lineage it was 60.

## Verdict handling (what the maker did)

- Re-derived each metric under the producing tool's exact lineage → all 6 required numbers
  MATCH within 1%, none mis-computed.
- The real defect was the **dual definition**, recorded as such: standardize one NK
  expression (`datetime(...'-18h')`) in both tools + resolve the doc's 72/73. Not "the
    number is wrong."

## Second-order caveats in the same session

- `hrv_window` is **hourly** buckets → `AVG(rmssd_mean)` is hour-weighted, not per-night.
  Fine for within-device comparisons; state it.
- HRV window date bound: `substr(start_utc,1,10)` (UTC) vs `date(start_utc,'localtime')`
  differ only at window edges; impact 58.9 vs 58.85 — a note, not a defect.
- Both tools opened the DB read-write though they only SELECT → flip to `mode=ro`.

## Reusable takeaway

When a number in a doc has two values, or a control value only matches "partially," assume
two definitions of one concept (lineage) before assuming bad arithmetic. Match against the
producing tool's exact expression; name the lineage on the number; the fix is standardizing
one definition, and the audit closes as confirmed-with-defect, not blocked.
