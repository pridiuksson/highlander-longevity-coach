#!/usr/bin/env python3
"""Cognitive appraisal and stress dialogue triage engine."""
from __future__ import annotations
import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional

CRISIS_PATTERNS = [
    r"\b(suicid(e|al)|kill\s+(my\s*self|myself))\b",
    r"\b(end\s+(it\s+all|my\s+life))\b",
    r"\b(want\s+to\s+die|better\s+off\s+dead)\b",
    r"\b(self[\s-]harm|cutting\s+myself|hurt\s+myself)\b",
    r"\b(can'?t\s+go\s+on\s+living)\b",
]

DEFAULT_CRISIS_MESSAGE = (
    "I hear how much pain you're experiencing right now, but I am an AI coach, "
    "not a crisis helpline or mental health clinician. Please connect with someone who can help right now:\n"
    "• In the US/Canada: Call or text 988 (Suicide & Crisis Lifeline)\n"
    "• In the UK: Call 111 (NHS) or 116 123 (Samaritans)\n"
    "• In Europe / International: Call 112 or visit findahelpline.com\n"
    "You do not have to carry this alone."
)


def check_crisis_red_flags(text: str) -> Optional[Dict[str, Any]]:
    """Scan for explicit self-harm or suicidal ideation markers."""
    normalized = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, normalized):
            return {
                "crisis_detected": True,
                "status": "CRISIS_HALT",
                "message": DEFAULT_CRISIS_MESSAGE,
            }
    return None


def classify_appraisal(text: str, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify subjective context and telemetry into an appraisal quadrant."""
    telemetry = telemetry or {}
    text_lower = text.lower()

    # Rule 1: Physiology-first check for Recovery Drain
    # If telemetry indicates multi-day sleep fragmentation or heavy recovery deficit
    if telemetry.get("sleep_fragmentation_high") or telemetry.get("multi_day_hrv_suppression"):
        return {
            "quadrant": "RECOVERY_DRAIN",
            "confidence": 0.85,
            "evidence": "Wearable telemetry indicates acute physiological deficit/sleep disruption",
            "perceived_control": "low",
        }

    # Contextual keywords
    eustress_keywords = ["deadline", "project", "presentation", "launch", "excited", "busy", "pushing", "momentum"]
    distress_keywords = ["overwhelmed", "trapped", "panicking", "panic", "helpless", "dread", "conflict", "fight", "boss", "anxious", "anxiety", "can't breathe"]
    drain_keywords = ["exhausted", "brain fog", "drained", "burned out", "burnout", "wiped out", "insomnia", "no sleep", "fatigued"]

    drain_score = sum(1 for kw in drain_keywords if kw in text_lower)
    distress_score = sum(1 for kw in distress_keywords if kw in text_lower)
    eustress_score = sum(1 for kw in eustress_keywords if kw in text_lower)

    if drain_score > max(distress_score, eustress_score):
        return {
            "quadrant": "RECOVERY_DRAIN",
            "confidence": 0.75,
            "evidence": "Subjective report emphasizes exhaustion, sleep deficit, and depleted capacity",
            "perceived_control": "low",
        }
    if distress_score > eustress_score:
        return {
            "quadrant": "DISTRESS",
            "confidence": 0.75,
            "evidence": "Subjective report emphasizes threat, loss of agency, or acute friction",
            "perceived_control": "low",
        }
    if eustress_score > 0 and distress_score == 0:
        return {
            "quadrant": "EUSTRESS",
            "confidence": 0.70,
            "evidence": "High challenge engagement with operational urgency but active control",
            "perceived_control": "high",
        }

    return {
        "quadrant": "UNCERTAIN",
        "confidence": 0.40,
        "evidence": "Ambiguous emotional/contextual valence",
        "perceived_control": "uncertain",
    }


def recommend_micro_action(quadrant: str, persona: str = "Protector") -> Dict[str, str]:
    """Prescribe exactly ONE tactical micro-action based on appraisal."""
    if quadrant == "EUSTRESS":
        return {
            "action_id": "single_task_lock",
            "title": "60-Minute Focus Boundary",
            "directive": "Pick your single highest-leverage deliverable. Mute notifications and execute for 60 minutes.",
        }
    elif quadrant == "DISTRESS":
        return {
            "action_id": "physiological_sigh",
            "title": "Cyclic Physiological Sighing",
            "directive": "Take two deep nasal inhales followed by one prolonged, audible oral exhale. Complete 5 repetitions right now.",
        }
    elif quadrant == "RECOVERY_DRAIN":
        return {
            "action_id": "early_sleep_window",
            "title": "Enforce Early Sleep Window",
            "directive": "Shut down screens 45 minutes earlier tonight and dial tomorrow's training down to restorative walking.",
        }
    else:  # UNCERTAIN
        return {
            "action_id": "sensory_grounding",
            "title": "5-Minute Grounding Pause",
            "directive": "Step away from your desk. Drink a glass of water slowly and notice 3 physical objects around you.",
        }


class DialogueSession:
    """Bounded, anti-rumination stress dialogue session."""

    def __init__(self, max_turns: int = 3, persona: str = "Protector"):
        self.max_turns = max_turns
        self.persona = persona
        self.turn_count = 0
        self.status = "ACTIVE"
        self.appraisal: Optional[Dict[str, Any]] = None
        self.action: Optional[Dict[str, str]] = None
        self.turns: List[Dict[str, str]] = []

    def process_turn(self, user_input: str, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a conversational turn, returning the coach response."""
        # 1. Crisis Interlock check
        crisis = check_crisis_red_flags(user_input)
        if crisis:
            self.status = "CRISIS_HALT"
            return crisis

        self.turn_count += 1
        self.turns.append({"role": "user", "text": user_input})

        # 2. Appraisal classification
        self.appraisal = classify_appraisal(user_input, telemetry)
        quadrant = self.appraisal["quadrant"]

        # 3. Decision: continue dialogue or deliver micro-action
        # If we have reached max_turns or have a clear non-uncertain classification
        if self.turn_count >= self.max_turns or quadrant != "UNCERTAIN":
            self.action = recommend_micro_action(quadrant, self.persona)
            self.status = "COMPLETED"

            # Validate-first framing: warm recognition before micro-action
            response_text = (
                f"I hear you. That is a real demand on your system right now.\n"
                f"Let's focus on one concrete step rather than untangling everything at once:\n\n"
                f"**{self.action['title']}**\n{self.action['directive']}\n\n"
                f"Take this one step. We can re-check how your recovery responds tomorrow."
            )
            return {
                "status": "COMPLETED",
                "turn": self.turn_count,
                "appraisal": self.appraisal,
                "action": self.action,
                "response": response_text,
            }
        else:
            # Uncertain and have budget: ask 1 targeted clarifying question
            response_text = (
                "I hear the strain. To help figure out what kind of support fits: "
                "does this feel more like an overwhelming pile of tasks, interpersonal tension, or pure physical exhaustion?"
            )
            return {
                "status": "ACTIVE",
                "turn": self.turn_count,
                "appraisal": self.appraisal,
                "response": response_text,
            }


def main():
    parser = argparse.ArgumentParser(description="Stress dialogue triage engine")
    parser.add_argument("--text", type=str, help="User input text")
    parser.add_argument("--telemetry-json", type=str, help="Optional JSON telemetry flags")
    parser.add_argument("--turn", type=int, default=1, help="Current turn number (1-based index)")
    parser.add_argument("--max-turns", type=int, default=3, help="Max conversational turns")
    parser.add_argument("--crisis-check", type=str, help="Quick standalone crisis check")
    parser.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args()

    if args.crisis_check:
        res = check_crisis_red_flags(args.crisis_check)
        if res:
            print(json.dumps(res, indent=2))
            sys.exit(0)
        else:
            print(json.dumps({"crisis_detected": False, "status": "SAFE"}))
            sys.exit(0)

    if not args.text:
        parser.print_help()
        sys.exit(1)

    telemetry = json.loads(args.telemetry_json) if args.telemetry_json else None
    session = DialogueSession(max_turns=args.max_turns)
    session.turn_count = max(0, args.turn - 1)
    result = session.process_turn(args.text, telemetry)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("crisis_detected"):
            print(result["message"])
        else:
            print(result["response"])


if __name__ == "__main__":
    main()
