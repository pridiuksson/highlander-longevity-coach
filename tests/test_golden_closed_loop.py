#!/usr/bin/env python3
"""Golden end-to-end integration test for the closed-loop stress coaching system.

Grounding: Section 5 of Research/stress-dialogue-loop.md
Exercises the full vertical loop:
1. INGEST / DETECT: 28-day baseline + slope break detection + workout confounder check
2. DECIDE / TRIAGE: 3-turn cognitive appraisal triage + single micro-action selection
3. LEARN / REBOUND: Next-night biometric recovery verification in SQLite with confounder gating
"""
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "health" / "wearable-health-data" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "decision" / "stress-dialogue" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "health" / "biometric-recovery-ledger" / "scripts"))

import baseline_math
import dialogue_triage
import rebound_tracker


class TestGoldenClosedLoop(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "health.db"
        self.conn = rebound_tracker.get_connection(self.db_path)
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
            CREATE TABLE IF NOT EXISTS heart_rate (
                ts_utc TEXT,
                min_hr REAL,
                mean_hr REAL
            );
        """)

        # Anchor date: 2026-10-03
        self.anchor_date = datetime(2026, 10, 3).date()

        # Populate 35 days:
        # Days 0 to 27: 28-day stable baseline vitals and regular workouts
        # Days 28 to 34: 7-day evaluation window with autonomic drop
        for i in range(35):
            dt = self.anchor_date - timedelta(days=35 - i)
            noise = float((i % 5) - 2)  # -2 to +2 variation
            val = (60.0 + noise) if i < 28 else (44.0 + (noise * 0.5))

            for h in (2, 3, 4):
                self.conn.execute(
                    "INSERT INTO hrv_window VALUES (?, ?)",
                    (f"{dt.isoformat()} {h:02d}:00:00", val),
                )
            self.conn.execute(
                "INSERT INTO workout VALUES (?, 300.0, 1800.0)",
                (f"{dt.isoformat()} 17:00:00",),
            )
            self.conn.execute(
                "INSERT INTO heart_rate VALUES (?, 58.0, 65.0)",
                (f"{dt.isoformat()} 06:00:00",),
            )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_golden_loop_worked_example(self):
        """Execute the full worked example from stress-dialogue-loop.md Section 5."""
        # =====================================================================
        # STAGE 1: DETECT & CONVOLUTION CHECK
        # =====================================================================
        # Smartwatch shows HRV slope break; recovery drops; training volume is flat.
        scan_res = baseline_math.scan_database(self.db_path, "2026-10-03", device_source="samsung")

        self.assertEqual(scan_res["metric_name"], "nocturnal_rmssd")
        self.assertEqual(scan_res["status"], "UNEXPLAINED_AUTONOMIC_DIP")
        self.assertEqual(scan_res["category"], "COGNITIVE_TRIAGE_CANDIDATE")
        self.assertFalse(scan_res["suppress_outreach"])
        self.assertLess(scan_res["rmssd"]["z_score"], -1.5)

        baseline_mean = scan_res["rmssd"]["baseline_mean"]
        baseline_std = scan_res["rmssd"]["baseline_std"]
        trough_sigma = scan_res["rmssd"]["z_score"]

        # =====================================================================
        # STAGE 2: PRE-DECIDE COGNITIVE APPRAISAL TRIAGE
        # =====================================================================
        # User shares subjective testimony of responsibility shift and friction
        user_testimony = (
            "Ever since my colleague left the team, I silently absorbed their responsibilities. "
            "My internal critic says just handle it and do not complain, but I am completely overwhelmed and exhausted."
        )

        session = dialogue_triage.DialogueSession(max_turns=3)
        turn_res = session.process_turn(user_testimony)

        self.assertEqual(turn_res["status"], "COMPLETED")
        self.assertEqual(turn_res["appraisal"]["quadrant"], "DISTRESS")
        self.assertIsNotNone(turn_res["action"])
        action_id = turn_res["action"]["action_id"]

        # Ledger check-in into biometric_rebound_events
        event_id = rebound_tracker.record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            deviation_sigma=trough_sigma,
            intervention_id=action_id,
            intervention_type=turn_res["action"]["title"],
            attributed_cause="responsibility_shift_workload",
            subjective_rating=4,
        )
        self.assertTrue(event_id.startswith("evt_20261003_"))

        # =====================================================================
        # STAGE 3: NEXT-DAY BIOMETRIC REBOUND VERIFICATION (Clean Case)
        # =====================================================================
        # Subsequent night (2026-10-04): vitals rebound toward baseline
        # No alcohol consumed, light recovery workout session
        next_date = "2026-10-04"
        self.conn.execute(f"INSERT INTO hrv_window VALUES ('{next_date} 03:00:00', 59.5)")
        self.conn.execute(f"INSERT INTO workout VALUES ('{next_date} 17:00:00', 200.0, 1500.0)")
        self.conn.commit()

        auto_res = rebound_tracker.auto_verify_event(
            db_path=self.db_path,
            event_id=event_id,
            manual_confounders={"alcohol": False, "late_meal": False},
        )

        self.assertEqual(auto_res["status"], "resolved")
        self.assertTrue(auto_res["is_recovered"])
        self.assertFalse(auto_res["has_confounder"])
        self.assertGreater(auto_res["rebound_delta_sigma"], 1.0)

        # Check ledger report
        rep = rebound_tracker.generate_report(self.db_path)
        action_title = turn_res["action"]["title"]
        self.assertEqual(rep["interventions"][action_title]["unconfounded_rebound_count"], 1)

    def test_golden_loop_confounded_rebound(self):
        """Rebound occurs, but alcohol was consumed -> must mark confounded, not resolved."""
        event_id = rebound_tracker.record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-2.0,
            intervention_id="act_01",
            intervention_type="Physiological Sigh",
        )

        next_date = "2026-10-04"
        self.conn.execute(f"INSERT INTO hrv_window VALUES ('{next_date} 03:00:00', 60.0)")
        self.conn.commit()

        auto_res = rebound_tracker.auto_verify_event(
            db_path=self.db_path,
            event_id=event_id,
            manual_confounders={"alcohol": True},
        )
        self.assertEqual(auto_res["status"], "confounded")
        self.assertTrue(auto_res["has_confounder"])

    def test_golden_loop_failed_rebound(self):
        """Vitals do not recover and plunge further -> must mark unresolved."""
        event_id = rebound_tracker.record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-2.0,
            intervention_id="act_01",
            intervention_type="Physiological Sigh",
        )

        next_date = "2026-10-04"
        # RMSSD stays depressed at 42.0 ms
        self.conn.execute(f"INSERT INTO hrv_window VALUES ('{next_date} 03:00:00', 42.0)")
        self.conn.commit()

        auto_res = rebound_tracker.auto_verify_event(
            db_path=self.db_path,
            event_id=event_id,
            manual_confounders={"alcohol": False},
        )
        self.assertEqual(auto_res["status"], "unresolved")
        self.assertFalse(auto_res["is_recovered"])


if __name__ == "__main__":
    unittest.main()
