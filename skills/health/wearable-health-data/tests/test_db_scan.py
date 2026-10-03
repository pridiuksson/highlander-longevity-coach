#!/usr/bin/env python3
"""Unit tests for SQLite database table scanning in baseline_math."""
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from baseline_math import scan_database


class TestDatabaseScan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "health.db"
        self.conn = sqlite3.connect(str(self.db_path))

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_samsung_schema_scan(self):
        """Scan Samsung Health tables (hrv_window, workout) for baseline and slope break."""
        self.conn.executescript("""
            CREATE TABLE hrv_window (
                start_utc TEXT,
                rmssd_mean REAL
            );
            CREATE TABLE workout (
                start_utc TEXT,
                calorie REAL,
                duration_s REAL
            );
        """)

        # Populate 35 days:
        # Days 0 to 27: baseline readings
        # Days 28 to 34: eval window readings with drop
        anchor_date = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor_date - timedelta(days=35 - i)
            noise = float((i % 5) - 2)  # -2 to +2 variation
            val = (60.0 + noise) if i < 28 else 45.0
            # 3 hourly samples per night
            for h in (2, 3, 4):
                self.conn.execute(
                    "INSERT INTO hrv_window VALUES (?, ?)",
                    (f"{dt.isoformat()} {h:02d}:00:00", val),
                )
            # Baseline workout energy
            self.conn.execute(
                "INSERT INTO workout VALUES (?, 300.0, 1800.0)",
                (f"{dt.isoformat()} 17:00:00",),
            )
        self.conn.commit()

        # Scan on 2026-10-03 -> unexplained dip
        res = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(res["metric_name"], "nocturnal_rmssd")
        self.assertEqual(res["status"], "UNEXPLAINED_AUTONOMIC_DIP")
        self.assertFalse(res["suppress_outreach"])
        self.assertEqual(res["eval_samples"], 7)
        self.assertEqual(res["base_samples"], 28)

    def test_apple_schema_scan(self):
        """Scan Apple Health tables (hrv_sdnn, workouts, resting_hr)."""
        self.conn.executescript("""
            CREATE TABLE hrv_sdnn (
                ts TEXT,
                value REAL
            );
            CREATE TABLE workouts (
                start TEXT,
                energy_kcal REAL,
                duration_min REAL
            );
            CREATE TABLE resting_hr (
                date TEXT,
                value REAL
            );
        """)

        anchor_date = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor_date - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            val = (50.0 + noise) if i < 28 else 35.0
            self.conn.execute("INSERT INTO hrv_sdnn VALUES (?, ?)", (f"{dt.isoformat()} 05:00:00", val))
            self.conn.execute("INSERT INTO resting_hr VALUES (?, ?)", (dt.isoformat(), 58.0))
            self.conn.execute("INSERT INTO workouts VALUES (?, 300.0, 45.0)", (f"{dt.isoformat()} 16:00:00",))

        # Add heavy workout on prior day (2026-10-02) -> elevated energy expenditure
        self.conn.execute(
            "UPDATE workouts SET energy_kcal = 800.0, duration_min = 90.0 WHERE substr(start, 1, 10) = '2026-10-02'"
        )
        self.conn.commit()

        # Scan on 2026-10-03 -> should be explained by heavy workout (suppressed)
        res = scan_database(self.db_path, "2026-10-03", device_source="apple")
        self.assertEqual(res["metric_name"], "hrv_sdnn")
        self.assertEqual(res["status"], "PHYSICAL_LOAD_CONFIRMED")
        self.assertTrue(res["suppress_outreach"])


if __name__ == "__main__":
    unittest.main()
