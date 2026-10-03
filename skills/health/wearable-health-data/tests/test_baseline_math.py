#!/usr/bin/env python3
"""Unit tests for baseline math, slope-break detection, and athletic confounders."""
import unittest
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from baseline_math import (
    calculate_baseline,
    detect_slope_break,
    evaluate_athletic_confounder,
    evaluate_biometric_state,
)


class TestBaselineMath(unittest.TestCase):
    def setUp(self):
        # 28 days of synthetic stable nocturnal RMSSD around 60ms +/- 6ms
        self.baseline_rmssd = [
            58.0, 62.0, 60.0, 61.0, 59.0, 63.0, 57.0, 60.0, 62.0, 58.0,
            61.0, 59.0, 64.0, 56.0, 60.0, 61.0, 58.0, 62.0, 60.0, 59.0,
            63.0, 57.0, 61.0, 60.0, 58.0, 62.0, 59.0, 61.0
        ]

    def test_calculate_baseline_min_samples(self):
        """Baseline must return None if fewer than 14 samples are present."""
        self.assertIsNone(calculate_baseline([60.0] * 13))
        res = calculate_baseline(self.baseline_rmssd)
        self.assertIsNotNone(res)
        mean, std = res
        self.assertAlmostEqual(mean, 60.0, delta=1.0)
        self.assertGreater(std, 1.0)

    def test_detect_slope_break_normal(self):
        """Evaluation window within 1.0 sigma does not trigger slope break."""
        b_mean, b_std = calculate_baseline(self.baseline_rmssd)
        eval_window = [59.0, 61.0, 58.0, 60.0, 62.0, 59.0, 60.0]  # mean ~59.8
        res = detect_slope_break(eval_window, b_mean, b_std)
        self.assertFalse(res["anomaly_detected"])

    def test_detect_slope_break_min_samples(self):
        """Single-night or fewer than 3 samples must not trigger a slope-break."""
        b_mean, b_std = calculate_baseline(self.baseline_rmssd)
        single_night = [40.0]
        res = detect_slope_break(single_night, b_mean, b_std, min_eval_samples=3)
        self.assertFalse(res["anomaly_detected"])
        self.assertIn("Fewer than", res["reason"])

    def test_detect_slope_break_dip(self):
        """Evaluation window dropping below 1.5 sigma triggers slope break."""
        b_mean, b_std = calculate_baseline(self.baseline_rmssd)
        eval_window = [45.0, 48.0, 46.0, 44.0, 47.0, 45.0, 46.0]  # mean ~45.8, z < -5.0
        res = detect_slope_break(eval_window, b_mean, b_std)
        self.assertTrue(res["anomaly_detected"])
        self.assertLess(res["z_score"], -1.5)

    def test_athletic_confounder_acute_heavy_session(self):
        """Acute heavy workout suppresses proactive mental stress outreach."""
        res = evaluate_athletic_confounder(
            prior_day_kcal=750.0,
            prior_day_duration_mins=90.0,
            persistent_dip_days=1,
        )
        self.assertEqual(res["status"], "PHYSICAL_LOAD_CONFIRMED")
        self.assertEqual(res["category"], "ATHLETIC_RECOVERY")
        self.assertTrue(res["suppress_outreach"])

    def test_athletic_confounder_overtraining_carveout(self):
        """Persistent multi-day dip (>=3 days) with high load indicates overtraining and is NOT suppressed."""
        res = evaluate_athletic_confounder(
            prior_day_kcal=750.0,
            prior_day_duration_mins=90.0,
            persistent_dip_days=3,
        )
        self.assertEqual(res["status"], "OVERTRAINING_RISK")
        self.assertEqual(res["category"], "PHYSICAL_DELOAD")
        self.assertFalse(res["suppress_outreach"])

    def test_unexplained_autonomic_dip(self):
        """Autonomic dip without prior-day athletic load surfaces for cognitive triage."""
        res = evaluate_athletic_confounder(
            prior_day_kcal=150.0,
            prior_day_duration_mins=20.0,
            persistent_dip_days=1,
        )
        self.assertEqual(res["status"], "UNEXPLAINED_AUTONOMIC_DIP")
        self.assertEqual(res["category"], "COGNITIVE_TRIAGE_CANDIDATE")
        self.assertFalse(res["suppress_outreach"])

    def test_full_biometric_state_integration(self):
        """Full pipeline flags unexplained dip and suppresses acute workout dip."""
        dip_eval = [45.0, 46.0, 47.0, 44.0, 45.0, 46.0, 45.0]

        # Case A: Low workout -> Candidate for triage
        res_a = evaluate_biometric_state(
            self.baseline_rmssd, dip_eval, workout_context={"prior_day_kcal": 100.0}
        )
        self.assertEqual(res_a["status"], "UNEXPLAINED_AUTONOMIC_DIP")
        self.assertFalse(res_a["suppress_outreach"])

        # Case B: Heavy workout -> Athletic recovery (suppressed)
        res_b = evaluate_biometric_state(
            self.baseline_rmssd, dip_eval, workout_context={"prior_day_kcal": 800.0}
        )
        self.assertEqual(res_b["status"], "PHYSICAL_LOAD_CONFIRMED")
        self.assertTrue(res_b["suppress_outreach"])


if __name__ == "__main__":
    unittest.main()
