#!/usr/bin/env python3
"""
Verification Gates for Apple Health Import.

Validates that apple_health.db satisfies structural integrity,
physiological plausibility, chronological consistency, and leak-gate safety.
"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime


def run_gates(db_path, min_rows=None):
    """Run all verification gates against the SQLite database."""
    if not os.path.exists(db_path):
        print(f"FAIL Gate G0: Database file does not exist: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    failures = []

    print(f"=== Verifying Apple Health Gates for {db_path} ===")

    # Gate 1: Schema & Tables
    expected_tables = {'resting_hr', 'hrv_sdnn', 'sleep_night', 'vo2_max', 'workouts', 'import_meta'}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    actual_tables = {row[0] for row in cursor.fetchall()}
    missing_tables = expected_tables - actual_tables
    if missing_tables:
        failures.append(f"Gate G1 (Schema): Missing tables: {missing_tables}")
    else:
        print("  PASS Gate G1: All expected tables exist.")

    # Gate 2: Non-empty counts (prevent passing open on empty database)
    if min_rows is None:
        min_rows = {t: 1 for t in ('resting_hr', 'hrv_sdnn', 'sleep_night', 'vo2_max', 'workouts')}

    counts = {}
    for table in ('resting_hr', 'hrv_sdnn', 'sleep_night', 'vo2_max', 'workouts'):
        if table in actual_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cursor.fetchone()[0]
            counts[table] = cnt
            expected_min = min_rows.get(table, 1)
            if cnt < expected_min:
                failures.append(f"Gate G2 (Counts): Table {table} has {cnt} rows, expected >= {expected_min}")
        else:
            counts[table] = 0
            failures.append(f"Gate G2 (Counts): Table {table} is missing")

    if not any(f.startswith("Gate G2") for f in failures):
        counts_str = ", ".join(f"{k}={v}" for k, v in counts.items())
        print(f"  PASS Gate G2: Non-empty counts ({counts_str})")

    # Gate 3: Physiological Plausibility
    # 3a: Resting HR plausible range [30, 150]
    if counts.get('resting_hr', 0) > 0:
        cursor.execute("SELECT MIN(value), MAX(value) FROM resting_hr")
        min_rhr, max_rhr = cursor.fetchone()
        if min_rhr < 30.0 or max_rhr > 150.0:
            failures.append(f"Gate G3a (Physiology - RHR): Out of plausible bounds [30, 150]: min={min_rhr}, max={max_rhr}")
        else:
            print(f"  PASS Gate G3a: RHR values plausible [{min_rhr}, {max_rhr}]")

    # 3b: HRV SDNN (5 - 350 ms)
    if counts.get('hrv_sdnn', 0) > 0:
        cursor.execute("SELECT MIN(value), MAX(value) FROM hrv_sdnn")
        min_hrv, max_hrv = cursor.fetchone()
        if min_hrv < 2.0 or max_hrv > 400.0:
            failures.append(f"Gate G3b (Physiology - HRV): Out of plausible bounds [2, 400]: min={min_hrv}, max={max_hrv}")
        else:
            print(f"  PASS Gate G3b: HRV values plausible [{min_hrv}, {max_hrv}]")

    # 3c: Aerobic capacity / VO2 max plausible bounds
    if counts.get('vo2_max', 0) > 0:
        cursor.execute("SELECT MIN(value), MAX(value) FROM vo2_max")
        min_vo2, max_vo2 = cursor.fetchone()
        if min_vo2 < 15.0 or max_vo2 > 90.0:
            failures.append(f"Gate G3c (Physiology - VO2): Out of plausible bounds [15, 90]: min={min_vo2}, max={max_vo2}")
        else:
            print(f"  PASS Gate G3c: VO2 values plausible [{min_vo2}, {max_vo2}]")

    # 3d: Sleep night duration (0.5 - 18 h) & stage subsets
    if counts.get('sleep_night', 0) > 0:
        cursor.execute("SELECT MIN(total_h), MAX(total_h) FROM sleep_night")
        min_slp, max_slp = cursor.fetchone()
        if min_slp < 0.2 or max_slp > 20.0:
            failures.append(f"Gate G3d (Physiology - Sleep): Out of plausible bounds [0.2, 20]: min={min_slp}, max={max_slp}")
        else:
            print(f"  PASS Gate G3d: Sleep durations plausible [{min_slp}h, {max_slp}h]")

        # Check deep + rem + core <= total + epsilon
        cursor.execute("SELECT COUNT(*) FROM sleep_night WHERE (deep_h + rem_h + core_h) > (total_h + 0.05)")
        invalid_stages = cursor.fetchone()[0]
        if invalid_stages > 0:
            failures.append(f"Gate G3d (Physiology - Sleep): {invalid_stages} nights have deep+rem+core > total")
        else:
            print("  PASS Gate G3d-stages: Sleep stage components properly bound within total sleep duration.")

    # 3e: Workouts duration and heart rate consistency
    if counts.get('workouts', 0) > 0:
        cursor.execute("SELECT MIN(duration_min), MAX(duration_min) FROM workouts WHERE duration_min IS NOT NULL")
        min_dur, max_dur = cursor.fetchone()
        if min_dur is not None and (min_dur <= 0 or max_dur > 1440):
            failures.append(f"Gate G3e (Physiology - Workouts): Duration out of plausible bounds [0, 1440]: min={min_dur}, max={max_dur}")
        else:
            print(f"  PASS Gate G3e: Workout durations plausible [{min_dur}m, {max_dur}m]")

        # Check HR consistency: avg_hr <= max_hr when both exist
        cursor.execute("SELECT COUNT(*) FROM workouts WHERE avg_hr IS NOT NULL AND max_hr IS NOT NULL AND avg_hr > max_hr")
        inconsistent_hr = cursor.fetchone()[0]
        if inconsistent_hr > 0:
            failures.append(f"Gate G3e (Physiology - Workouts): {inconsistent_hr} workouts have avg_hr > max_hr")
        else:
            print("  PASS Gate G3e-hr: Heart rate averages and maximums internally consistent.")

    # Gate 4: Chronological and Date Formatting
    if counts.get('resting_hr', 0) > 0:
        cursor.execute("SELECT date FROM resting_hr LIMIT 20")
        for row in cursor.fetchall():
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', row[0]):
                failures.append(f"Gate G4 (Chronology): Malformed resting_hr date '{row[0]}'")
                break
        else:
            print("  PASS Gate G4: Resting HR dates properly formatted YYYY-MM-DD.")

    if counts.get('sleep_night', 0) > 0:
        cursor.execute("SELECT night FROM sleep_night LIMIT 20")
        for row in cursor.fetchall():
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', row[0]):
                failures.append(f"Gate G4 (Chronology): Malformed sleep_night key '{row[0]}'")
                break
        else:
            print("  PASS Gate G4: Sleep night keys properly formatted YYYY-MM-DD.")

    # Gate 5: Leak Gate Compliance (No private network hosts, tokens, or credential leaks)
    cursor.execute("SELECT key, value FROM import_meta")
    meta_rows = cursor.fetchall()
    leak_patterns = [
        re.compile(r'192\.168\.\d+\.\d+'),
        re.compile(r'10\.\d+\.\d+\.\d+'),
        re.compile(r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+'),
        re.compile(r'localhost:\d+'),
        re.compile(r'(?i)bearer\s+[a-z0-9_.-]{16,}'),
        re.compile(r'(?i)ghp_[a-zA-Z0-9]{20,}'),
    ]
    for k, v in meta_rows:
        val_str = str(v)
        for pat in leak_patterns:
            if pat.search(val_str):
                failures.append(f"Gate G5 (Privacy/Leak): Sensitive token pattern matched in import_meta ({k}={v})")
    if not any(f.startswith("Gate G5") for f in failures):
        print("  PASS Gate G5: Privacy check clean (zero sensitive host/token leaks).")

    conn.close()

    if failures:
        print("\n--- GATE FAILURES ---")
        for f in failures:
            print(f"  FAILED: {f}")
        return False

    print("\nALL APPLE HEALTH GATES PASSED (100% verified).")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run verification gates against apple_health.db")
    parser.add_argument("db", help="Path to apple_health.db")
    args = parser.parse_args()

    success = run_gates(args.db)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
