"""Pure library wrapper for the biometric recovery rebound tracker."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import _recovery_impl as _mod


def record_intervention(db_path: Path, **kw) -> str:
    return _mod.record_intervention(db_path, **kw)


def verify_next_day_rebound(db_path: Path, event_id: str, **kw) -> Dict[str, Any]:
    return _mod.verify_next_day_rebound(db_path, event_id, **kw)


def auto_verify_event(db_path: Path, event_id: str, manual_confounders: Any = None) -> Dict[str, Any]:
    """Verify an event against next-night data. manual_confounders (optional dict) is passed through."""
    return _mod.auto_verify_event(db_path, event_id, manual_confounders=manual_confounders)


def expire_stale_events(db_path: Path, max_age_hours: int = 48) -> int:
    return _mod.expire_stale_events(db_path, max_age_hours)


def generate_report(db_path: Path) -> Dict[str, Any]:
    return _mod.generate_report(db_path)


def get_verified_hypotheses(db_path: Path, min_n: int = 10) -> List[Dict[str, Any]]:
    return _mod.get_verified_hypotheses(db_path, min_n)


def generate_weekly_recap(db_path: Path) -> str:
    return _mod.generate_weekly_recap(db_path)