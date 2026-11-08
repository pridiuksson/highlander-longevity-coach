"""Pure library wrapper for the stress-dialogue triage engine."""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import _triage_impl as _mod


def check_crisis(text: str) -> Optional[Dict[str, Any]]:
    return _mod.check_crisis_red_flags(text)


def classify(text: str, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _mod.classify_appraisal(text, telemetry)


def recommend(quadrant: str, persona: str = "Protector") -> Dict[str, str]:
    return _mod.recommend_micro_action(quadrant, persona)