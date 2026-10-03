#!/usr/bin/env python3
"""Unit tests for automatic SQLite next-day recovery verification."""
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
import sys

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from rebound_tracker import (
    record_intervention,
    auto_verify_event,
    get_connection,
)


class TestAutoVerify(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "health.db"
        self.conn = get_connection(self.db_path)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS hrv_window (
                start_utc TEXT,
                rmssd_mean REAL
            );
            CREATE TABLE IF NOT EXISTS workout (
                start_utc TEXT,
                calorie REAL,
                duration_s REAL
            );
        """)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_auto_verify_clean_rebound(self):
        """Auto-verify finds next night vitals in hrv_window and marks resolved."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-2.0,
            intervention_id="act_sigh_01",
            intervention_type="physiological_sigh",
        )

        # Populate next night (2026-10-04) with recovered vitals (59.0 ms -> delta = +1.8 sigma)
        self.conn.execute("INSERT INTO hrv_window VALUES ('2026-10-04 03:00:00', 59.0)")
        self.conn.execute("INSERT INTO workout VALUES ('2026-10-04 17:00:00', 250.0, 1800.0)")
        self.conn.commit()

        res = auto_verify_event(self.db_path, eid)
        self.assertEqual(res["status"], "resolved")
        self.assertTrue(res["is_recovered"])
        self.assertAlmostEqual(res["rebound_delta_sigma"], 1.8, delta=0.01)

    def test_auto_verify_heavy_workout_confounder(self):
        """Auto-verify detects prior-day heavy workout in workout table and marks confounded."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-2.0,
            intervention_id="act_sigh_02",
            intervention_type="physiological_sigh",
        )

        # Populate next night with recovered vitals but high athletic strain session
        self.conn.execute("INSERT INTO hrv_window VALUES ('2026-10-04 03:00:00', 62.0)")
        self.conn.execute("INSERT INTO workout VALUES ('2026-10-04 17:00:00', 750.0, 5400.0)")
        self.conn.commit()

        res = auto_verify_event(self.db_path, eid)
        self.assertEqual(res["status"], "confounded")
        self.assertTrue(res["has_confounder"])
        self.assertTrue(res["confounder_flags"].get("heavy_training"))

    def test_auto_verify_missing_vitals_fresh_vs_expired(self):
        """Fresh missing vitals return pending; >48h old missing vitals transition to expired."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-1.8,
            intervention_id="act_sigh_03",
            intervention_type="physiological_sigh",
        )

        # Fresh event without next-night vitals -> pending
        res = auto_verify_event(self.db_path, eid)
        self.assertEqual(res["status"], "pending")

        # Age the event beyond 48 hours
        old_ts = int(time.time()) - (50 * 3600)
        self.conn.execute("UPDATE biometric_rebound_events SET created_ts = ? WHERE event_id = ?", (old_ts, eid))
        self.conn.commit()

        res_expired = auto_verify_event(self.db_path, eid)
        self.assertEqual(res_expired["status"], "expired")


if __name__ == "__main__":
    unittest.main()
