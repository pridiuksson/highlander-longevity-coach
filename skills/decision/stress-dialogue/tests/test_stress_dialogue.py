#!/usr/bin/env python3
"""Unit tests for stress dialogue triage and safety interlock."""
import unittest
import sys
from pathlib import Path

# Add scripts directory
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from dialogue_triage import (
    check_crisis_red_flags,
    classify_appraisal,
    recommend_micro_action,
    DialogueSession,
    ephemeral_audio_scratch,
)
import tempfile
import os


class TestStressDialogue(unittest.TestCase):
    def test_crisis_red_flag_detection(self):
        """Crisis expressions must immediately trigger CRISIS_HALT."""
        inputs = [
            "I want to kill myself",
            "thinking about suicide today",
            "I want to end my life",
            "feeling like I want to self-harm",
            "better off dead honestly",
        ]
        for text in inputs:
            res = check_crisis_red_flags(text)
            self.assertIsNotNone(res, f"Failed to detect crisis in: {text}")
            self.assertTrue(res["crisis_detected"])
            self.assertEqual(res["status"], "CRISIS_HALT")
            self.assertIn("988", res["message"])

    def test_safe_inputs_no_false_positive_crisis(self):
        """Standard athletic or work stress expressions must not trigger crisis halt."""
        safe_inputs = [
            "that deadlift workout killed my back",
            "this deadline is murder",
            "I am dying to see the new results",
            "cutting calories for the summer",
        ]
        for text in safe_inputs:
            res = check_crisis_red_flags(text)
            self.assertIsNone(res, f"False positive crisis on safe input: {text}")

    def test_appraisal_classification_distress(self):
        """Threat and overwhelmed expressions map to DISTRESS."""
        res = classify_appraisal("I am completely overwhelmed and panicking about this conflict with my manager")
        self.assertEqual(res["quadrant"], "DISTRESS")
        self.assertEqual(res["perceived_control"], "low")

    def test_appraisal_classification_eustress(self):
        """Active deadline push with momentum maps to EUSTRESS."""
        res = classify_appraisal("Big launch deadline tomorrow, pushing hard through the project milestones")
        self.assertEqual(res["quadrant"], "EUSTRESS")
        self.assertEqual(res["perceived_control"], "high")

    def test_appraisal_classification_recovery_drain(self):
        """Exhaustion and sleep deficit map to RECOVERY_DRAIN."""
        res = classify_appraisal("Total brain fog, exhausted, feeling burned out and haven't slept well in days")
        self.assertEqual(res["quadrant"], "RECOVERY_DRAIN")

    def test_physiology_first_override(self):
        """Wearable telemetry indicating multi-day deficit forces RECOVERY_DRAIN regardless of text."""
        telemetry = {"sleep_fragmentation_high": True, "multi_day_hrv_suppression": True}
        res = classify_appraisal("I feel fine, just busy with a launch", telemetry=telemetry)
        self.assertEqual(res["quadrant"], "RECOVERY_DRAIN")
        self.assertIn("Wearable telemetry", res["evidence"])

    def test_dialogue_session_bounded_turns(self):
        """Session must terminate and recommend 1 action within max_turns."""
        session = DialogueSession(max_turns=2)
        # Turn 1: ambiguous input
        res1 = session.process_turn("I don't know, things just feel slightly off today")
        if res1["status"] == "ACTIVE":
            # Turn 2: reaches cap
            res2 = session.process_turn("Still not sure what to make of it")
            self.assertEqual(res2["status"], "COMPLETED")
            self.assertIsNotNone(res2["action"])
        else:
            self.assertEqual(res1["status"], "COMPLETED")

    def test_crisis_halts_dialogue_session(self):
        """A crisis turn in a session halts immediately without continuing dialogue."""
        session = DialogueSession()
        res = session.process_turn("I feel like I want to die")
        self.assertEqual(session.status, "CRISIS_HALT")
        self.assertTrue(res["crisis_detected"])
        self.assertIn("988", res["message"])

    def test_voice_acoustic_fail_safe(self):
        """Empty audio transcript or low confidence must trigger fail-safe grounding."""
        session = DialogueSession()
        # Case 1: Empty transcript from unparseable audio
        res1 = session.process_voice_input("")
        self.assertEqual(res1["status"], "FAIL_SAFE")
        self.assertIn("988", res1["message"])

        # Case 2: Low confidence audio under acoustic distortion
        res2 = session.process_voice_input("garbled audio", is_low_confidence=True)
        self.assertEqual(res2["status"], "FAIL_SAFE")
        self.assertIn("112", res2["message"])

    def test_ephemeral_audio_scratch_cleanup(self):
        """Audio scratch files must be strictly unlinked upon context exit."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            tmp_path = tmp.name
            tmp.write(b"dummy audio bytes")

        self.assertTrue(os.path.exists(tmp_path))

        with ephemeral_audio_scratch(tmp_path):
            self.assertTrue(os.path.exists(tmp_path))

        self.assertFalse(os.path.exists(tmp_path))


if __name__ == "__main__":
    unittest.main()
