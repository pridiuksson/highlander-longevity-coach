#!/usr/bin/env python3
"""Sleep-era analysis over $HERMES_HOME/data/health.db: monthly wake/HR-rise + sleep metrics,
winter-vs-winter same-season comparison, and the HR-rise physiological-wake proxy.

Usage: python3 sleep_era_analysis.py            (full monthly table + era summary)
       python3 sleep_era_analysis.py --bp 2026-01   (explicit breakpoint YYYY-MM)

Key measurement rules encoded here (see references/sleep-analysis-findings.md):
- ALL analysis on ts_utc (ts_local mixes the Vilnius/Stockholm zones).
- Night-key: substr(datetime(start_utc,'-18 hours'),1,10).
- Wake = morning HR-rise hour (first hour 03-10 where HR >= night-min+12),
  NOT tracked session end (watch stops at detected wake, user stays in bed).
- Era comparisons: winter-vs-winter only (photoperiod dominates; adjacent-month
  comparisons and rolling-mean breakpoint detection manufacture false steps).
"""
import os
import sqlite3
import sys
from collections import defaultdict

DB = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), "data/health.db")
BP = None
if len(sys.argv) > 2 and sys.argv[1] == '--bp':
    BP = sys.argv[2]

con = sqlite3.connect(DB)
cur = con.cursor()


def sto_hour(ts_utc, mo):
    summer = int(mo[5:7]) in (4, 5, 6, 7, 8, 9, 10)
    return (int(ts_utc[11:13]) + (2 if summer else 1)) % 24


# 1) HR-rise hour per day
days = defaultdict(list)
for ts, hr in cur.execute("SELECT ts_utc, hr FROM heart_rate WHERE hr IS NOT NULL"):
    days[ts[:10]].append((sto_hour(ts, ts[:7]), hr))

rise = {}
for d, bins in days.items():
    night = [h for hh, h in bins if 0 <= hh <= 5]
    if not night:
        continue
    base = min(night)
    for hh, h in sorted(bins):
        if 3 <= hh <= 10 and h >= base + 12:
            rise[d] = hh
            break

# 2) night metrics
sess = {}
for nk, dur, eff in cur.execute('''WITH n AS (
  SELECT substr(datetime(substr(start_utc,1,19), '-18 hours'),1,10) nk,
         SUM((julianday(end_utc)-julianday(start_utc))*86400) dur_s, MAX(efficiency) eff
  FROM sleep_session GROUP BY nk)
  SELECT nk, dur_s, eff FROM n WHERE dur_s BETWEEN 10800 AND 43200'''):
    sess[nk] = (dur / 3600.0, eff)

stage_nights = defaultdict(lambda: defaultdict(float))
for stage, s, dur in cur.execute("SELECT stage, start_utc, duration_s FROM sleep_stage_named"):
    if s:
        stage_nights[s[:10]][stage] += (dur or 0) / 60.0

night_hr = defaultdict(list)
for ts, mn in cur.execute("SELECT ts_utc, min_hr FROM heart_rate WHERE min_hr IS NOT NULL"):
    night_hr[ts[:10]].append(mn)

print(f'{"month":9} {"rise_h":>6} {"n":>4} | {"dur":>5} {"deep":>5} {"REM":>5} {"light":>5} {"awake":>5} {"eff":>5} {"slpHR":>5}')
rows = []
for mo in sorted(set(list(rise_d[:7] for rise_d in rise) + list(nk[:7] for nk in sess))):
    s_nights = [nk for nk in sess if nk[:7] == mo]
    r = [h for d, h in rise.items() if d[:7] == mo]
    if not r or not s_nights:
        continue
    n = len(s_nights)
    st = defaultdict(float)
    for nk in s_nights:
        for k, v in stage_nights.get(nk, {}).items():
            st[k] += v
    effs = [sess[nk][1] for nk in s_nights if sess[nk][1]]
    hrs = [h for nk in s_nights for h in night_hr.get(nk, [])]
    row = (mo, sum(r) / len(r), len(r), sum(sess[nk][0] for nk in s_nights) / n,
           st.get('deep', 0) / n, st.get('rem', 0) / n, st.get('light', 0) / n,
           st.get('awake', 0) / n, sum(effs) / len(effs) if effs else float('nan'),
           sum(hrs) / len(hrs) if hrs else float('nan'))
    rows.append(row)
    print(f'{row[0]:9} {row[1]:6.2f} {row[2]:4} | {row[3]:5.2f} {row[4]:5.0f} {row[5]:5.0f} {row[6]:5.0f} {row[7]:5.0f} {row[8]:5.1f} {row[9]:5.1f}')

# 3) same-season (Dec/Jan) comparison table
print('\n=== winter-vs-winter (Dec+Jan nights) ===')
print(f'{"winter":11} {"rise":>5} {"dur":>5} {"deep":>5} {"REM":>5} {"awake":>5} {"eff":>5}')
for y in range(2021, 2026):
    mos = [f'{y}-12', f'{y + 1}-01']
    wr = [r for r in rows if r[0] in mos]
    if not wr:
        continue
    print(f'{y}/{y + 1 - 2000:02d}    {sum(r[1] for r in wr) / len(wr):5.2f} '
          f'{sum(r[3] for r in wr) / len(wr):5.2f} {sum(r[4] for r in wr) / len(wr):5.0f} '
          f'{sum(r[5] for r in wr) / len(wr):5.0f} {sum(r[7] for r in wr) / len(wr):5.0f} '
          f'{sum(r[8] for r in wr) / len(wr):5.1f}')

# 4) era summary at breakpoint
bp = BP or '2026-04'


def agg(sel):
    n = len(sel)
    return {k: sum(r[i] for r in sel) / n for i, k in enumerate(
        ['mo', 'rise', 'n', 'dur', 'deep', 'rem', 'light', 'awake', 'eff', 'slphr']) if k != 'mo' and k != 'n'}


b, a = agg([r for r in rows if r[0] < bp]), agg([r for r in rows if r[0] >= bp])
print(f'\nBEFORE {bp}: ' + '  '.join(f'{k}={v:.1f}' for k, v in b.items()))
print(f'AFTER  {bp}: ' + '  '.join(f'{k}={v:.1f}' for k, v in a.items()))
print('(NOTE: era deltas at a single breakpoint are confounded by season — '
      'prefer the winter-vs-winter table above for "did X change my sleep" questions.)')
con.close()
