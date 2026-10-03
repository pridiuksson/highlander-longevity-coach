#!/usr/bin/env python3
"""Unit tests for biometric recovery ledger and confounder exclusion."""
from pathlib import Path
import tempfile
import time
import unittest
import sys

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from rebound_tracker import (
    record_intervention,
    verify_next_day_rebound,
    expire_stale_events,
    generate_report,
    get_verified_hypotheses,
    get_connection,
)


class TestReboundTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "health.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_unconfounded_verify(self):
        """Clean verification sets status to resolved and calculates rebound sigma."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-1.8,
            intervention_id="act_sigh_01",
            intervention_type="physiological_sigh",
            attributed_cause="deadline_crunch",
            subjective_rating=4,
        )
        self.assertTrue(eid.startswith("evt_20261003_"))

        # Verify next night with synthetic recovery reading and no confounders
        res = verify_next_day_rebound(
            db_path=self.db_path,
            event_id=eid,
            next_night_rmssd=59.0,
            confounder_flags={"alcohol": False, "late_meal": False},
        )
        self.assertEqual(res["status"], "resolved")
        self.assertAlmostEqual(res["rebound_sigma"], -0.2, delta=0.01)
        self.assertAlmostEqual(res["rebound_delta_sigma"], 1.6, delta=0.01)

    def test_unresolved_recovery_failure(self):
        """When vitals do not rebound and stay depressed, status is unresolved."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-10-03",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-1.8,
            intervention_id="act_sigh_unres",
            intervention_type="physiological_sigh",
        )

        # Next night RMSSD is even lower (48.0 ms -> z = -2.4 sigma)
        res = verify_next_day_rebound(
            db_path=self.db_path,
            event_id=eid,
            next_night_rmssd=48.0,
            confounder_flags={"alcohol": False, "late_meal": False},
        )
        self.assertEqual(res["status"], "unresolved")
        self.assertFalse(res["is_recovered"])

    def test_confounder_exclusion(self):
        """Presence of alcohol or late meal sets status to confounded."""
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

        res = verify_next_day_rebound(
            db_path=self.db_path,
            event_id=eid,
            next_night_rmssd=62.0,  # Rebounded, but confounded by alcohol
            confounder_flags={"alcohol": True, "late_meal": False},
        )
        self.assertEqual(res["status"], "confounded")
        self.assertTrue(res["has_confounder"])

    def test_expire_stale_events(self):
        """Pending events older than 48h transition to expired."""
        eid = record_intervention(
            db_path=self.db_path,
            date_str="2026-09-28",
            trigger_metric="nocturnal_rmssd",
            baseline_mean=60.0,
            baseline_std=5.0,
            deviation_sigma=-1.5,
            intervention_id="act_walk_01",
            intervention_type="grounding_walk",
        )

        # Force created_ts to 72 hours ago
        old_ts = int(time.time()) - (72 * 3600)
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE biometric_rebound_events SET created_ts = ? WHERE event_id = ?",
                (old_ts, eid),
            )

        n = expire_stale_events(self.db_path, max_age_hours=48)
        self.assertEqual(n, 1)

        rep = generate_report(self.db_path)
        self.assertEqual(rep["interventions"]["grounding_walk"]["expired_count"], 1)

    def test_report_and_hypotheses_threshold(self):
        """Hypotheses require N >= 10 unconfounded observations."""
        # Record 10 unconfounded events for physiological_sigh
        for i in range(10):
            eid = record_intervention(
                db_path=self.db_path,
                date_str=f"2026-09-{i+1:02d}",
                trigger_metric="nocturnal_rmssd",
                baseline_mean=60.0,
                baseline_std=5.0,
                deviation_sigma=-1.6,
                intervention_id=f"act_sigh_{i}",
                intervention_type="physiological_sigh",
                subjective_rating=4,
            )
            verify_next_day_rebound(
                db_path=self.db_path,
                event_id=eid,
                next_night_rmssd=58.0 + (i % 3),
                confounder_flags={"alcohol": False},
            )

        # Record 3 events for early_sleep_window (below N=10 threshold)
        for i in range(3):
            eid = record_intervention(
                db_path=self.db_path,
                date_str=f"2026-08-{i+1:02d}",
                trigger_metric="nocturnal_rmssd",
                baseline_mean=60.0,
                baseline_std=5.0,
                deviation_sigma=-1.8,
                intervention_id=f"act_sleep_{i}",
                intervention_type="early_sleep_window",
            )
            verify_next_day_rebound(
                db_path=self.db_path,
                event_id=eid,
                next_night_rmssd=61.0,
                confounder_flags={"alcohol": False},
            )

        rep = generate_report(self.db_path)
        self.assertEqual(rep["interventions"]["physiological_sigh"]["unconfounded_rebound_count"], 10)
        self.assertEqual(rep["interventions"]["early_sleep_window"]["unconfounded_rebound_count"], 3)

        hyp = get_verified_hypotheses(self.db_path, min_observations=10)
        self.assertEqual(len(hyp), 1)
        self.assertEqual(hyp[0]["intervention_type"], "physiological_sigh")
        self.assertIn("non-causal", hyp[0]["epistemic_statement"])

    def test_hypotheses_delta_sigma_filter(self):
        """Interventions with N >= 10 but marginal delta (< 1.0 sigma) must not be promoted."""
        # 10 unconfounded events where rebound delta is +0.8 sigma (resolved, but < 1.0 delta threshold)
        for i in range(10):
            eid = record_intervention(
                db_path=self.db_path,
                date_str=f"2026-07-{i+1:02d}",
                trigger_metric="nocturnal_rmssd",
                baseline_mean=60.0,
                baseline_std=5.0,
                deviation_sigma=-1.5,
                intervention_id=f"act_marginal_{i}",
                intervention_type="marginal_stretch",
            )
            # Next night is 56.5 (sigma = -0.7, delta = +0.8)
            verify_next_day_rebound(
                db_path=self.db_path,
                event_id=eid,
                next_night_rmssd=56.5,
                confounder_flags={"alcohol": False},
            )

        # With default min_delta=1.0, marginal_stretch must NOT qualify
        hyp = get_verified_hypotheses(
            self.db_path,
            min_observations=10,
            min_rebound_delta_sigma=1.0,
        )
        marginal_hyp = [h for h in hyp if h["intervention_type"] == "marginal_stretch"]
        self.assertEqual(len(marginal_hyp), 0)

        # But if threshold is 0.7, it qualifies
        hyp_low = get_verified_hypotheses(
            self.db_path,
            min_observations=10,
            min_rebound_delta_sigma=0.7,
        )
        marginal_low = [h for h in hyp_low if h["intervention_type"] == "marginal_stretch"]
        self.assertEqual(len(marginal_low), 1)


if __name__ == "__main__":
    unittest.main()
