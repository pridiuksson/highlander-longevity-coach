#!/usr/bin/env python3
"""Insight outcome ledger — O2/O3 fragment adopted from arXiv 2605.06717.

Every proactive delivery gets an entry; outcomes close the learning loop so
silence becomes learned instead of merely configured.

Usage:
  ledger.py add SOURCE CLASS HEADLINE...      # prints new entry id
  ledger.py resolve ID acted|ignored|corrected|dropped
  ledger.py report [--json]                   # stats + recommendations, prunes >90d
  ledger.py reflect [--json]                  # schedule recommendations (read-only)
  ledger.py pending                           # unresolved entries

Stdlib only. Concurrency-safe via fcntl lock. File: $HERMES_HOME/scripts/.state/insight-ledger.jsonl
"""
import datetime as dt
import fcntl
import json
import os
import sys
from collections import defaultdict

LEDGER = os.environ.get(
    "HERMES_LEDGER", os.path.expanduser(os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), "scripts/.state/insight-ledger.jsonl"))
)
LOCK = LEDGER + ".lock"
PRUNE_DAYS = 90
PAUSE_STREAK = 3          # consecutive ignored ...
PAUSE_SPAN_DAYS = 7       # ... AND streak must span at least this many days
# --- reflect: schedule recommendations (stage 7). Never auto-applied. ---
REFLECT_MIN_SAMPLES = 5   # settled deliveries a source needs before a shift is suggested,
                          # and they must fall on this many separate delivery days
REFLECT_RECENCY_DAYS = 30  # ... inside this window, so a stale habit cannot drive it
REFLECT_FAST_LATENCY_H = 4  # ... with a median bookkeeping age at or under this
REFLECT_SHIFT_HOURS = 2   # one step from the recorded baseline, never cumulative
VALID_OUTCOMES = {"acted", "ignored", "corrected", "dropped"}


def _load():
    if not os.path.exists(LEDGER):
        return []
    entries = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # tolerate a torn line rather than crash delivery-time callers
    return entries


def _save(entries):
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, LEDGER)


def _locked(fn):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        return fn()


def _now():
    return dt.datetime.now(dt.timezone.utc)


def cmd_add(source, cls, headline):
    entry = {
        "id": str(int(_now().timestamp() * 1000)),
        "ts": int(_now().timestamp()),
        "source": source,
        "class": cls.upper(),
        "headline": headline,
        "status": "pending",
    }

    def write():
        with open(LEDGER, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry["id"]

    print(_locked(write))


def cmd_resolve(entry_id, outcome):
    if outcome not in VALID_OUTCOMES:
        sys.exit(f"outcome must be one of {sorted(VALID_OUTCOMES)}")

    def resolve():
        entries = _load()
        hit = False
        for e in entries:
            if e["id"] == entry_id and e["status"] == "pending":
                e["status"] = outcome
                e["resolved_ts"] = int(_now().timestamp())
                hit = True
        if hit:
            _save(entries)
        return hit

    if not _locked(resolve):
        sys.exit(f"no pending entry with id {entry_id}")
    print(f"resolved {entry_id} -> {outcome}")


def _report_data():
    now = _now()
    cutoff = now - dt.timedelta(days=PRUNE_DAYS)
    entries = _load()
    # prune old resolved entries (keep pending regardless of age)
    kept = [e for e in entries if e["status"] == "pending" or dt.datetime.fromtimestamp(e["ts"], dt.timezone.utc) > cutoff]
    if len(kept) != len(entries):
        _save(kept)
    return kept, now


def _analyze(entries, now):
    """Pure aggregation over ledger entries — no I/O and no pruning.

    `report` and `reflect` share this so the ignore-streak rule, the ALERT-class
    exclusion and the pending ages cannot drift apart between the two commands.
    """
    per = defaultdict(lambda: {"acted": 0, "ignored": 0, "corrected": 0, "dropped": 0, "pending": 0})
    # track ignore streaks in delivery order
    ordered = sorted([e for e in entries if e["status"] != "pending"], key=lambda e: e["ts"])
    streak = defaultdict(int)       # consecutive ignored DIGEST deliveries, reset by acted/corrected
    streak_start = {}
    pause_candidates = {}
    alert_ignores = defaultdict(int)
    for e in ordered:
        s = e["status"]
        per[e["source"]][s] += 1
        if s == "ignored" and e["class"] == "ALERT":
            alert_ignores[e["source"]] += 1
            continue  # ALERT-class never counts toward pause candidacy
        if s == "ignored":
            streak[e["source"]] += 1
            streak_start.setdefault(e["source"], e["ts"])
        else:
            streak[e["source"]] = 0
            streak_start.pop(e["source"], None)
    for src, n in streak.items():
        if n >= PAUSE_STREAK and streak_start.get(src) is not None:
            span_days = (now - dt.datetime.fromtimestamp(streak_start[src], dt.timezone.utc)).days
            if span_days >= PAUSE_SPAN_DAYS:
                pause_candidates[src] = {"streak": n, "span_days": span_days}
    for e in entries:
        if e["status"] == "pending":
            per[e["source"]]["pending"] += 1
            per[e["source"]]["oldest_pending_age_h"] = max(
                per[e["source"]].get("oldest_pending_age_h", 0),
                int((now - dt.datetime.fromtimestamp(e["ts"], dt.timezone.utc)).total_seconds() / 3600),
            )
    return {
        "sources": per,
        "pause_candidates": pause_candidates,
        "alert_ignores": alert_ignores,
    }


def cmd_report(as_json=False):
    entries, now = _report_data()
    a = _analyze(entries, now)
    per, pause_candidates, alert_ignores = a["sources"], a["pause_candidates"], a["alert_ignores"]
    if as_json:
        print(json.dumps({"sources": dict(per), "pause_candidates": pause_candidates}, ensure_ascii=False, indent=2))
        return
    if not per:
        print("ledger empty — no deliveries recorded")
        return
    print(f"{'source':28} {'acted':>6} {'ign':>5} {'corr':>5} {'drop':>5} {'pend':>5}  note")
    for src, d in sorted(per.items()):
        note = ""
        if src in pause_candidates:
            note = f"PAUSE CANDIDATE (human-confirm): {pause_candidates[src]['streak']} consecutive ignored DIGEST over {pause_candidates[src]['span_days']}d"
        elif alert_ignores.get(src, 0) >= 3:
            note = "repeated ALERT-class ignores — fix the underlying failure, do NOT pause"
        elif d["ignored"] and not (d["acted"] or d["corrected"]):
            note = "all deliveries ignored — check utility"
        if d.get("pending"):
            note += f" | {d['pending']} pending (oldest {d.get('oldest_pending_age_h', 0)}h) — resolve at next contact"
        print(f"{src:28} {d['acted']:>6} {d['ignored']:>5} {d['corrected']:>5} {d['dropped']:>5} {d['pending']:>5}  {note}".rstrip())


def _median(values):
    n = len(values)
    if n == 0:
        return None
    mid = n // 2
    return values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2.0


def _reply_latency_h(entries, now):
    """Per-source (delivery_day, latency_h) samples, sorted by latency.

    `ts` is stamped when the delivery is ledgered; `resolved_ts` when the agent
    closes it. The gap is a bookkeeping age, not an observation of the user's
    clock — see SKILL.md on honest scope before reading anything into it. The
    delivery day is kept so five entries from one day cannot pass as five
    independent fast hits.
    """
    cutoff = now.timestamp() - REFLECT_RECENCY_DAYS * 86400
    per_source = defaultdict(list)
    for e in entries:
        if e["status"] in ("acted", "corrected") and e.get("resolved_ts") and e["ts"] >= cutoff:
            day = int(e["ts"] // 86400)  # UTC delivery day, for sample independence
            per_source[e["source"]].append((day, (e["resolved_ts"] - e["ts"]) / 3600.0))
    return {src: sorted(v, key=lambda pair: pair[1]) for src, v in per_source.items()}


def _window_ignored(entries, now):
    """Ignored count inside the recency window.

    A lifetime count would let one ignore from months ago block an acceleration
    forever, even after the source started landing every week.
    """
    cutoff = now.timestamp() - REFLECT_RECENCY_DAYS * 86400
    counts = defaultdict(int)
    for e in entries:
        if e["status"] == "ignored" and e["ts"] >= cutoff:
            counts[e["source"]] += 1
    return counts


def _recommendations(entries, now):
    """One schedule recommendation per source. Pure: reads entries, writes nothing."""
    a = _analyze(entries, now)
    latencies = _reply_latency_h(entries, now)
    ignored_recent = _window_ignored(entries, now)
    recs = []
    for src, d in sorted(a["sources"].items()):
        settled = d["acted"] or d["ignored"] or d["corrected"] or d["dropped"]
        if not settled:
            continue  # nothing has been delivered-and-closed yet; a schedule call now is noise
        action, offset = "hold", 0
        if a["alert_ignores"].get(src, 0) >= PAUSE_STREAK:
            action = "fix"
            reason = (f"{a['alert_ignores'][src]} ALERT-class ignores — the watcher is telling you "
                      f"something is broken; fix that, never pause an alert")
        elif src in a["pause_candidates"]:
            pc = a["pause_candidates"][src]
            action = "cooldown"
            reason = (f"{pc['streak']} consecutive ignored DIGESTs over {pc['span_days']}d "
                      f"— reduce cadence or pause (human-confirm)")
        else:
            sample = latencies.get(src, [])
            n = len(sample)
            distinct_days = len({day for day, _ in sample})
            med = _median([h for _, h in sample])
            if (n >= REFLECT_MIN_SAMPLES and distinct_days >= REFLECT_MIN_SAMPLES
                    and ignored_recent.get(src, 0) == 0
                    and med is not None and med <= REFLECT_FAST_LATENCY_H):
                action, offset = "shift_earlier", -REFLECT_SHIFT_HOURS
                reason = (f"{n} settled on {distinct_days} separate days in the last "
                          f"{REFLECT_RECENCY_DAYS}d, none ignored, median bookkeeping age "
                          f"{med:.1f}h — try one step earlier than the recorded baseline "
                          f"(human-confirm)")
            else:
                reason = "insufficient or mixed evidence — keep the current schedule"
        recs.append({
            "source": src,
            "action": action,
            "offset_hours": offset,
            "reason": reason,
            "counts": {k: d[k] for k in ("acted", "ignored", "corrected", "dropped", "pending") if k in d},
            "ignored_recent": ignored_recent.get(src, 0),
            "window_days": REFLECT_RECENCY_DAYS,
            "confirm_required": True,
        })
    return recs


def cmd_reflect(as_json=False):
    entries = _load()  # read-only: reflect never writes and never prunes
    recs = _recommendations(entries, _now())
    if as_json:
        print(json.dumps({"recommendations": recs}, ensure_ascii=False, indent=2))
        return
    if not recs:
        print("nothing to reflect on — no settled deliveries in the ledger")
        return
    print(f"{'source':28} {'action':14} {'offset':>7}  why")
    for r in recs:
        offset = f"{r['offset_hours']:+}h" if r["offset_hours"] else "—"
        print(f"{r['source']:28} {r['action']:14} {offset:>7}  {r['reason']}")


def cmd_pending():
    entries = _load()
    pend = [e for e in entries if e["status"] == "pending"]
    for e in sorted(pend, key=lambda e: e["ts"]):
        age_h = round((_now() - dt.datetime.fromtimestamp(e["ts"], dt.timezone.utc)).total_seconds() / 3600, 1)
        print(f"{e['id']}  {age_h:>8}h  {e['class']:6} {e['source']:24} {e['headline'][:60]}")
    if not pend:
        print("no pending entries")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "add" and len(args) >= 3:
        cmd_add(args[0], args[1], " ".join(args[2:]))
    elif cmd == "resolve" and len(args) == 2:
        cmd_resolve(args[0], args[1])
    elif cmd == "report":
        cmd_report(as_json="--json" in args)
    elif cmd == "reflect":
        cmd_reflect(as_json="--json" in args)
    elif cmd == "pending":
        cmd_pending()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
