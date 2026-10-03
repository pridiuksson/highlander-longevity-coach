#!/usr/bin/env python3
"""Unit tests for autonomic baseline monitoring and proactive delivery gating."""
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys

PROACTIVE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROACTIVE_ROOT / "scripts"))

# Import baseline_math from wearable-health-data
WEARABLE_ROOT = PROACTIVE_ROOT.parent.parent / "health" / "wearable-health-data"
sys.path.insert(0, str(WEARABLE_ROOT / "scripts"))

from baseline_math import scan_database
import ledger


def decide_autonomic_dispatch(scan_res: dict, recent_ledger_entries: list) -> dict:
    """Routing and delivery gate decision engine for autonomic telemetry."""
    status = scan_res.get("status")

    if status in ("NORMAL_VARIANCE", "INSUFFICIENT_BASELINE", "NO_NEW_DATA"):
        return {"action": "SILENT", "reason": f"Baseline stable or data sparse: {status}"}

    if status == "PHYSICAL_LOAD_CONFIRMED":
        return {
            "action": "SILENT",
            "reason": "Outreach suppressed: autonomic dip explained by acute workout load",
        }

    if status == "OVERTRAINING_RISK":
        return {
            "action": "DELIBERATE_DELOAD",
            "reason": "Persistent autonomic dip with continuous athletic exertion",
        }

    if status == "UNEXPLAINED_AUTONOMIC_DIP":
        # 5-test insight gate evaluation: 'New' test
        # Check if an autonomic outreach was already dispatched recently
        has_recent_outreach = any(
            e.get("source") == "stress-dialogue"
            and e.get("status") in ("pending", "acted")
            for e in recent_ledger_entries
        )
        if has_recent_outreach:
            return {
                "action": "SILENT",
                "gate_rejected": "New",
                "reason": "Consecutive autonomic dip already addressed in active outreach",
            }

        return {
            "action": "DISPATCH_STRESS_DIALOGUE",
            "reason": "Unexplained autonomic dip cleared delivery gate for pre-Decide triage",
        }

    return {"action": "SILENT", "reason": f"Unknown status: {status}"}


class TestAutonomicGating(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "health.db"
        self.conn = sqlite3.connect(str(self.db_path))
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

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_normal_variance_silent(self):
        """Stable vitals within normal variance must produce SILENT outcome."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", 60.0 + noise))
            self.conn.execute("INSERT INTO workout VALUES (?, 300.0, 1800.0)", (f"{dt.isoformat()} 17:00:00",))
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(scan["status"], "NORMAL_VARIANCE")
        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=[])
        self.assertEqual(decision["action"], "SILENT")

    def test_insufficient_baseline_silent(self):
        """Sparse data (<14 days) must exit SILENT without hallucinating distress."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(5):
            dt = anchor - timedelta(days=5 - i)
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", 45.0))
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(scan["status"], "INSUFFICIENT_BASELINE")
        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=[])
        self.assertEqual(decision["action"], "SILENT")

    def test_acute_workout_confounder_suppressed(self):
        """Acute heavy workout suppresses cognitive outreach."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            val = (60.0 + noise) if i < 33 else 44.0
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", val))
            self.conn.execute("INSERT INTO workout VALUES (?, 300.0, 1800.0)", (f"{dt.isoformat()} 17:00:00",))

        # Heavy training session on prior day
        self.conn.execute("UPDATE workout SET calorie = 800.0, duration_s = 5400.0 WHERE substr(start_utc, 1, 10) = '2026-10-02'")
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(scan["status"], "PHYSICAL_LOAD_CONFIRMED")
        self.assertTrue(scan["suppress_outreach"])

        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=[])
        self.assertEqual(decision["action"], "SILENT")

    def test_overtraining_risk_deload(self):
        """Persistent dip (>= 3 days) with high training load triggers deload guidance."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            val = (60.0 + noise) if i < 30 else 44.0
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", val))
            self.conn.execute("INSERT INTO workout VALUES (?, 300.0, 1800.0)", (f"{dt.isoformat()} 17:00:00",))

        self.conn.execute("UPDATE workout SET calorie = 800.0, duration_s = 5400.0 WHERE substr(start_utc, 1, 10) = '2026-10-02'")
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(scan["status"], "OVERTRAINING_RISK")
        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=[])
        self.assertEqual(decision["action"], "DELIBERATE_DELOAD")

    def test_unexplained_dip_cleared_for_dialogue(self):
        """Unexplained autonomic dip without prior alerts dispatches to stress dialogue."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            val = (60.0 + noise) if i < 28 else 44.0
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", val))
            self.conn.execute("INSERT INTO workout VALUES (?, 300.0, 1800.0)", (f"{dt.isoformat()} 17:00:00",))
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        self.assertEqual(scan["status"], "UNEXPLAINED_AUTONOMIC_DIP")
        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=[])
        self.assertEqual(decision["action"], "DISPATCH_STRESS_DIALOGUE")

    def test_unexplained_dip_rejected_on_new_test_duplicate(self):
        """Consecutive dip where outreach was already sent yesterday is rejected by gate."""
        anchor = datetime(2026, 10, 3).date()
        for i in range(35):
            dt = anchor - timedelta(days=35 - i)
            noise = float((i % 5) - 2)
            val = (60.0 + noise) if i < 28 else 44.0
            self.conn.execute("INSERT INTO hrv_window VALUES (?, ?)", (f"{dt.isoformat()} 03:00:00", val))
            self.conn.execute("INSERT INTO workout VALUES (?, 300.0, 1800.0)", (f"{dt.isoformat()} 17:00:00",))
        self.conn.commit()

        scan = scan_database(self.db_path, "2026-10-03", device_source="samsung")
        existing_ledger = [
            {"id": 1, "source": "stress-dialogue", "status": "pending", "headline": "Autonomic check-in"}
        ]
        decision = decide_autonomic_dispatch(scan, recent_ledger_entries=existing_ledger)
        self.assertEqual(decision["action"], "SILENT")
        self.assertEqual(decision["gate_rejected"], "New")


if __name__ == "__main__":
    unittest.main()
