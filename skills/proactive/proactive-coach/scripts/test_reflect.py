#!/usr/bin/env python3
"""Tests for `ledger.py reflect` — the schedule recommendations.

Runs the real module against fixture ledgers in a temp directory, so the gate
constants (`PAUSE_STREAK`, `PAUSE_SPAN_DAYS`, `REFLECT_*`) are exercised as they
are actually shipped rather than restated here.

Usage:
  python3 scripts/test_reflect.py          # from the skill directory
Exit: 0 all cases pass, 1 at least one failed.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PY = os.path.join(HERE, "ledger.py")

DAY = 86400


def load_module(ledger_path):
    """Import ledger.py fresh, pointed at a throwaway ledger file."""
    os.environ["HERMES_LEDGER"] = ledger_path
    spec = importlib.util.spec_from_file_location("ledger_under_test", LEDGER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.LEDGER = ledger_path
    mod.LOCK = ledger_path + ".lock"
    return mod


def entry(source, status, age_days, cls="DIGEST", latency_h=None, now=None):
    """One ledger record, aged `age_days` back from now.

    `latency_h` sets resolved_ts — the bookkeeping gap reflect reads.
    """
    now = now or time.time()
    ts = int(now - age_days * DAY)
    e = {"id": f"{source}-{status}-{age_days}", "ts": ts, "source": source, "class": cls,
         "headline": "fixture", "status": status}
    if status != "pending":
        e["resolved_ts"] = int(ts + (latency_h or 0) * 3600)
    return e


def write_ledger(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def rec_for(recs, source):
    for r in recs:
        if r["source"] == source:
            return r
    return None


def run_case(name, entries, source, expect_action, failures):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "ledger.jsonl")
        write_ledger(path, entries)
        mod = load_module(path)
        before = open(path, encoding="utf-8").read()
        recs = mod._recommendations(mod._load(), mod._now())
        after = open(path, encoding="utf-8").read()
        r = rec_for(recs, source)
        got = r["action"] if r else None
        ok = got == expect_action
        untouched = before == after
        if not ok:
            failures.append(f"{name}: expected {expect_action!r}, got {got!r}")
        if not untouched:
            failures.append(f"{name}: reflect mutated the ledger (must be read-only)")
        print(f"  {'PASS' if ok and untouched else 'FAIL'}  {name}: {got}")
        return r


def main():
    now = time.time()
    failures = []
    print("ledger.py reflect — fixture cases")

    # --- gate must NOT fire on thin or short evidence -------------------------
    run_case("empty ledger", [], "s", None, failures)
    run_case("pending only (nothing settled)",
             [entry("s", "pending", 1, now=now)], "s", None, failures)
    run_case("two ignored DIGESTs (below streak)",
             [entry("s", "ignored", 9, now=now), entry("s", "ignored", 2, now=now)],
             "s", "hold", failures)
    run_case("three ignored DIGESTs inside a 3-day span",
             [entry("s", "ignored", 3, now=now), entry("s", "ignored", 2, now=now),
              entry("s", "ignored", 1, now=now)], "s", "hold", failures)

    # --- gate fires on sustained ignore --------------------------------------
    decel = run_case("three ignored DIGESTs over an 8-day span",
                     [entry("s", "ignored", 9, now=now), entry("s", "ignored", 5, now=now),
                      entry("s", "ignored", 1, now=now)], "s", "cooldown", failures)
    if decel and decel["offset_hours"] != 0:
        failures.append("cooldown must not carry a time offset; cadence is the lever")

    # a streak broken by a reaction is not a streak
    run_case("ignored, acted, ignored, ignored (streak reset)",
             [entry("s", "ignored", 10, now=now), entry("s", "acted", 7, now=now, latency_h=1),
              entry("s", "ignored", 5, now=now), entry("s", "ignored", 1, now=now)],
             "s", "hold", failures)

    # --- ALERT is never a cooldown candidate ---------------------------------
    alert = run_case("three ignored ALERTs",
                     [entry("a", "ignored", 9, cls="ALERT", now=now),
                      entry("a", "ignored", 5, cls="ALERT", now=now),
                      entry("a", "ignored", 1, cls="ALERT", now=now)], "a", "fix", failures)
    if alert and alert["offset_hours"] != 0:
        failures.append("fix must not carry an offset")

    # --- acceleration needs the full evidence bar ----------------------------
    five_acted = [entry("e", "acted", 20 - i, now=now, latency_h=1) for i in range(5)]
    shift = run_case("five acted, 1h bookkeeping age, none ignored", five_acted, "e", "shift_earlier", failures)
    if shift and shift["offset_hours"] >= 0:
        failures.append("shift_earlier must carry a negative offset")
    if shift and shift["confirm_required"] is not True:
        failures.append("every recommendation must require confirmation")

    four_acted = [entry("e", "acted", 20 - i, now=now, latency_h=1) for i in range(4)]
    run_case("four acted (below REFLECT_MIN_SAMPLES)", four_acted, "e", "hold", failures)

    slow = [entry("e", "acted", 20 - i, now=now, latency_h=30) for i in range(5)]
    run_case("five acted but 30h bookkeeping age", slow, "e", "hold", failures)

    mixed = five_acted + [entry("e", "ignored", 1, now=now)]
    run_case("five acted plus one ignored in the window", mixed, "e", "hold", failures)

    old_ignore = five_acted + [entry("e", "ignored", 60, now=now)]
    run_case("five acted, one ignore older than the window",
             old_ignore, "e", "shift_earlier", failures)

    stale = [entry("e", "acted", 45 + i, now=now, latency_h=1) for i in range(5)]
    run_case("five acted but outside the recency window", stale, "e", "hold", failures)

    burst = [entry("e", "acted", 20, now=now, latency_h=0.05) for _ in range(5)]
    run_case("five acted on a single delivery day (same-session burst)",
             burst, "e", "hold", failures)

    four_days = [entry("e", "acted", 20 - i, now=now, latency_h=1) for i in range(4)] + \
                [entry("e", "acted", 19, now=now, latency_h=1)]
    run_case("five acted but only four separate delivery days",
             four_days, "e", "hold", failures)

    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("OK: all reflect cases behave as specified")


if __name__ == "__main__":
    main()
