"""longevity-coach plugin — health coaching loop for Hermes.

Registers 9 config-free skills, an automation blueprint for the weekly crunch,
9 typed tools, and a manual-trigger coach_run_crunch for demos.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict

from . import tools
from .tools import ledger, triage, recovery

_REPO_ROOT = Path(__file__).resolve().parent
_SKILLS_DIR = _REPO_ROOT / "skills"


def _skill_path(name: str) -> Path:
    # skills/<category>/<name>/SKILL.md
    for p in _SKILLS_DIR.rglob(f"{name}/SKILL.md"):
        return p
    raise FileNotFoundError(f"skill not found: {name}")


# ---- allowlisted config-free skills bundled as plugin skills ----
_BUNDLED_SKILLS = [
    "grill", "loop", "peer-review", "plan", "find-evidence",
    "supplement-spec-verification", "meal-planning", "swedish-food-nutrition",
    "schedule-management",
]


def _ledger_db() -> Path:
    home = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    return home / "scripts" / ".state" / "insight-ledger.jsonl"


def _recovery_db() -> Path:
    home = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    return home / "data" / "health.db"


# ---- tool handlers ----

def _coach_ledger_add(args: Dict[str, Any]) -> str:
    return ledger.add(
        source=args.get("source", "manual"),
        cls=args.get("cls", "DIGEST"),
        headline=args.get("headline", ""),
        dedup_key=args.get("dedup_key"),
    )


def _coach_ledger_resolve(args: Dict[str, Any]) -> str:
    return ledger.resolve(args["entry_id"], args["outcome"])


def _coach_ledger_report(args: Dict[str, Any]) -> str:
    return ledger.report(as_json=bool(args.get("as_json", False)))


def _coach_ledger_reflect(args: Dict[str, Any]) -> str:
    return ledger.reflect(as_json=bool(args.get("as_json", False)))


def _coach_stress_triage(args: Dict[str, Any]) -> str:
    text = args.get("text", "")
    crisis = triage.check_crisis(text)
    if crisis is not None:
        return json.dumps(crisis, ensure_ascii=False)
    appr = triage.classify(text)
    micro = triage.recommend(appr.get("quadrant", "UNCERTAIN"))
    return json.dumps({"appraisal": appr, "micro_action": micro}, ensure_ascii=False)


def _coach_recovery_record(args: Dict[str, Any]) -> str:
    db = Path(args.get("db_path") or _recovery_db())
    eid = recovery.record_intervention(
        db_path=db,
        date_str=args["date_str"],
        trigger_metric=args["trigger_metric"],
        baseline_mean=float(args["baseline_mean"]),
        baseline_std=float(args["baseline_std"]),
        deviation_sigma=float(args["deviation_sigma"]),
        intervention_id=args["intervention_id"],
        intervention_type=args["intervention_type"],
        attributed_cause=args.get("attributed_cause"),
        subjective_rating=args.get("subjective_rating"),
    )
    return eid


def _coach_recovery_verify(args: Dict[str, Any]) -> str:
    db = Path(args.get("db_path") or _recovery_db())
    res = recovery.auto_verify_event(db, args["event_id"])
    return json.dumps(res, ensure_ascii=False, default=str)


def _coach_recovery_report(args: Dict[str, Any]) -> str:
    db = Path(args.get("db_path") or _recovery_db())
    rep = recovery.generate_report(db)
    return json.dumps(rep, ensure_ascii=False, default=str)


def _coach_run_crunch(args: Dict[str, Any]) -> str:
    demo = bool(args.get("demo", False))
    text = args.get("text", "")
    if demo and not text:
        text = "I feel tired and overwhelmed after a busy week."
    parts = []
    if demo:
        parts.append("[DEMO / SYNTHETIC DATA — no writes to live ledger or health.db]")
    crisis = triage.check_crisis(text)
    if crisis is not None:
        parts.append("CRISIS: " + crisis["message"])
    else:
        appr = triage.classify(text)
        micro = triage.recommend(appr.get("quadrant", "UNCERTAIN"))
        parts.append("appraisal=" + json.dumps(appr))
        parts.append("micro_action=" + json.dumps(micro))
    if demo:
        parts.append("ledger_report=DEMO: 1 pending entry (synthetic, not persisted)")
        parts.append("recovery_report=DEMO: {\"interventions\": {}}")
    else:
        parts.append("ledger_report=" + ledger.report())
        db = Path(args.get("db_path") or _recovery_db())
        try:
            parts.append("recovery_report=" + json.dumps(recovery.generate_report(db), default=str))
        except Exception as e:
            parts.append("recovery_report_error=" + str(e))
    return "\n".join(parts)


# ---- tool schemas ----
_LEDGER_ADD_SCHEMA = {
    "type": "object",
    "properties": {
        "source": {"type": "string", "description": "Source stream of the delivery"},
        "cls": {"type": "string", "description": "ALERT or DIGEST", "enum": ["ALERT", "DIGEST"]},
        "headline": {"type": "string", "description": "One-line headline"},
        "dedup_key": {"type": "string", "description": "Optional dedup key"},
    },
    "required": ["source", "cls", "headline"],
}

_LEDGER_RESOLVE_SCHEMA = {
    "type": "object",
    "properties": {
        "entry_id": {"type": "string"},
        "outcome": {"type": "string", "enum": ["acted", "ignored", "corrected", "dropped", "silent"]},
    },
    "required": ["entry_id", "outcome"],
}

_EMPTY_SCHEMA = {"type": "object", "properties": {}}

_STRESS_TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string", "description": "User text to triage"}},
    "required": ["text"],
}

_RECOVERY_RECORD_SCHEMA = {
    "type": "object",
    "properties": {
        "date_str": {"type": "string", "description": "YYYY-MM-DD"},
        "trigger_metric": {"type": "string"},
        "baseline_mean": {"type": "number"},
        "baseline_std": {"type": "number"},
        "deviation_sigma": {"type": "number"},
        "intervention_id": {"type": "string"},
        "intervention_type": {"type": "string"},
        "attributed_cause": {"type": "string"},
        "subjective_rating": {"type": "integer"},
        "db_path": {"type": "string"},
    },
    "required": ["date_str", "trigger_metric", "baseline_mean", "baseline_std",
                 "deviation_sigma", "intervention_id", "intervention_type"],
}

_RECOVERY_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "db_path": {"type": "string"},
    },
    "required": ["event_id"],
}

_RECOVERY_REPORT_SCHEMA = {
    "type": "object",
    "properties": {"db_path": {"type": "string"}},
}

_RUN_CRUNCH_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Optional text to triage during the crunch"},
        "demo": {"type": "boolean", "description": "Run in demo mode with synthetic data (no persistence)"},
        "db_path": {"type": "string"},
    },
}


def register(ctx) -> None:
    # ---- skills ----
    for skill_name in _BUNDLED_SKILLS:
        skill_md = _skill_path(skill_name)
        ctx.register_skill(skill_name, skill_md)

    # ---- automation blueprint ----
    ctx.register_automation_blueprint(
        "weekly-crunch",
        title="Weekly health crunch",
        description="Weekly proactive coaching crunch: stress triage, recovery scoring, ledger report.",
        category="health",
        schedule_template="{minute} {hour} * * 1",
        prompt_template=(
            "Run the weekly health crunch: triage recent autonomic data with stress-dialogue, "
            "score biometric recovery, and report the insight ledger. Deliver one insight or stay silent."
        ),
        slots=[
            {"name": "time", "type": "time", "label": "What time?", "default": "09:00"},
            {"name": "deliver", "type": "enum", "label": "Where?", "default": "origin",
             "options": ["origin", "local"], "strict": False},
        ],
        skills=[],
        tags=["health", "proactive"],
    )

    # ---- tools ----
    ctx.register_tool("coach_ledger_add", "longevity-coach", _LEDGER_ADD_SCHEMA, _coach_ledger_add,
                      description="Add an entry to the insight outcome ledger.")
    ctx.register_tool("coach_ledger_resolve", "longevity-coach", _LEDGER_RESOLVE_SCHEMA, _coach_ledger_resolve,
                      description="Resolve a ledger entry with an outcome.")
    ctx.register_tool("coach_ledger_report", "longevity-coach", _EMPTY_SCHEMA, _coach_ledger_report,
                      description="Report ledger stats and recommendations.")
    ctx.register_tool("coach_ledger_reflect", "longevity-coach", _EMPTY_SCHEMA, _coach_ledger_reflect,
                      description="Reflect on ledger data for schedule recommendations.")
    ctx.register_tool("coach_stress_triage", "longevity-coach", _STRESS_TRIAGE_SCHEMA, _coach_stress_triage,
                      description="Stress triage: crisis check + appraisal + micro-action.")
    ctx.register_tool("coach_recovery_record", "longevity-coach", _RECOVERY_RECORD_SCHEMA, _coach_recovery_record,
                      description="Record a biometric recovery intervention event.")
    ctx.register_tool("coach_recovery_verify", "longevity-coach", _RECOVERY_VERIFY_SCHEMA, _coach_recovery_verify,
                      description="Auto-verify a recovery event against next-night data.")
    ctx.register_tool("coach_recovery_report", "longevity-coach", _RECOVERY_REPORT_SCHEMA, _coach_recovery_report,
                      description="Generate a recovery intervention report.")
    ctx.register_tool("coach_run_crunch", "longevity-coach", _RUN_CRUNCH_SCHEMA, _coach_run_crunch,
                      description="Manual trigger for the weekly health crunch (demo).")
