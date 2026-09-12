#!/usr/bin/env python3
"""Insight outcome ledger — O2/O3 fragment adopted from arXiv 2605.06717.

Every proactive delivery gets an entry; outcomes close the learning loop so
silence becomes learned instead of merely configured.

Usage:
  ledger.py add SOURCE CLASS HEADLINE...      # prints new entry id
  ledger.py resolve ID acted|ignored|corrected|dropped
  ledger.py report [--json]                   # stats + recommendations, prunes >90d
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


def cmd_report(as_json=False):
    entries, now = _report_data()
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
    elif cmd == "pending":
        cmd_pending()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
