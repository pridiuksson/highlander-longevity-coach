#!/usr/bin/env python3
"""Closed-loop somatic recovery and biometric rebound ledger."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional
import uuid

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS biometric_rebound_events (
    event_id TEXT PRIMARY KEY,
    date_str TEXT NOT NULL,
    trigger_metric TEXT NOT NULL,
    baseline_mean REAL NOT NULL,
    baseline_std REAL NOT NULL,
    deviation_sigma REAL NOT NULL,
    intervention_id TEXT NOT NULL,
    intervention_type TEXT NOT NULL,
    attributed_cause TEXT,
    subjective_rating INTEGER,
    next_night_rmssd REAL,
    rebound_sigma REAL,
    rebound_delta_sigma REAL,
    confounder_flags TEXT,
    created_ts INTEGER NOT NULL,
    resolved_ts INTEGER,
    status TEXT CHECK(status IN ('pending', 'resolved', 'unresolved', 'confounded', 'expired'))
);
CREATE INDEX IF NOT EXISTS idx_rebound_date ON biometric_rebound_events (date_str);
CREATE INDEX IF NOT EXISTS idx_rebound_status ON biometric_rebound_events (status);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open connection, set WAL mode, busy timeout, and ensure schema is initialized."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        conn.executescript(SCHEMA_SQL)
    return conn


def record_intervention(
    db_path: Path,
    date_str: str,
    trigger_metric: str,
    baseline_mean: float,
    baseline_std: float,
    deviation_sigma: float,
    intervention_id: str,
    intervention_type: str,
    attributed_cause: Optional[str] = None,
    subjective_rating: Optional[int] = None,
) -> str:
    try:
        parsed_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValueError(f"date_str must be strictly formatted as YYYY-MM-DD, got {date_str!r}")
    date_prefix = parsed_dt.strftime("%Y%m%d")
    event_id = f"evt_{date_prefix}_{uuid.uuid4().hex[:8]}"
    created_ts = int(time.time())

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO biometric_rebound_events (
                event_id, date_str, trigger_metric, baseline_mean, baseline_std,
                deviation_sigma, intervention_id, intervention_type, attributed_cause,
                subjective_rating, created_ts, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                event_id, date_str, trigger_metric, baseline_mean, baseline_std,
                deviation_sigma, intervention_id, intervention_type, attributed_cause,
                subjective_rating, created_ts
            ),
        )
    return event_id


def verify_next_day_rebound(
    db_path: Path,
    event_id: str,
    next_night_rmssd: float,
    confounder_flags: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """Evaluate next-day biometric rebound and enforce confounder exclusion."""
    confounder_flags = confounder_flags or {}
    resolved_ts = int(time.time())

    # Check confounders
    has_confounder = any(
        confounder_flags.get(k, False)
        for k in ("alcohol", "late_meal", "bedtime_drift", "heavy_training")
    )
    new_status = "confounded" if has_confounder else "resolved"

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM biometric_rebound_events WHERE event_id = ?", (event_id,)
        ).fetchone()

        if not row:
            raise KeyError(f"Event not found: {event_id}")

        baseline_mean = row["baseline_mean"]
        baseline_std = row["baseline_std"]
        trough_sigma = row["deviation_sigma"]

        rebound_sigma = (
            round((next_night_rmssd - baseline_mean) / baseline_std, 2)
            if baseline_std > 0
            else 0.0
        )
        rebound_delta_sigma = round(rebound_sigma - trough_sigma, 2)

        # Physiological recovery condition: vitals rebound within 1.0 sigma of baseline
        # or improve by at least +0.5 sigma from the trough
        is_recovered = (rebound_sigma >= -1.0) or (rebound_delta_sigma >= 0.5)

        if has_confounder:
            new_status = "confounded"
        elif is_recovered:
            new_status = "resolved"
        else:
            new_status = "unresolved"

        conn.execute(
            """
            UPDATE biometric_rebound_events
            SET next_night_rmssd = ?, rebound_sigma = ?, rebound_delta_sigma = ?,
                confounder_flags = ?, resolved_ts = ?, status = ?
            WHERE event_id = ?
            """,
            (
                next_night_rmssd,
                rebound_sigma,
                rebound_delta_sigma,
                json.dumps(confounder_flags),
                resolved_ts,
                new_status,
                event_id,
            ),
        )

    return {
        "event_id": event_id,
        "status": new_status,
        "rebound_sigma": rebound_sigma,
        "rebound_delta_sigma": rebound_delta_sigma,
        "is_recovered": is_recovered,
        "has_confounder": has_confounder,
        "confounder_flags": confounder_flags,
    }


def auto_verify_event(
    db_path: Path,
    event_id: str,
    manual_confounders: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """Look up subsequent night vitals in health.db and automatically verify rebound."""
    manual_confounders = manual_confounders or {}
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM biometric_rebound_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"Event not found: {event_id}")

        date_str = row["date_str"]
        target_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        next_date_str = (target_dt + timedelta(days=1)).isoformat()

        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }

        next_val = None
        if "hrv_window" in tables:
            r = conn.execute(
                """
                SELECT AVG(rmssd_mean) as val
                FROM hrv_window
                WHERE substr(start_utc, 1, 10) = ? AND rmssd_mean > 0 AND rmssd_mean < 250
                """,
                (next_date_str,),
            ).fetchone()
            if r and r["val"] is not None:
                next_val = float(r["val"])
        elif "hrv_sdnn" in tables:
            r = conn.execute(
                """
                SELECT AVG(value) as val
                FROM hrv_sdnn
                WHERE substr(ts, 1, 10) = ?
                """,
                (next_date_str,),
            ).fetchone()
            if r and r["val"] is not None:
                next_val = float(r["val"])

        if next_val is None:
            age_hours = (int(time.time()) - row["created_ts"]) / 3600.0
            if age_hours > 48.0:
                conn.execute(
                    "UPDATE biometric_rebound_events SET status = 'expired' WHERE event_id = ?",
                    (event_id,),
                )
                return {"event_id": event_id, "status": "expired", "reason": "No vitals landed within 48h"}
            return {
                "event_id": event_id,
                "status": "pending",
                "reason": f"No vitals found in database for subsequent night {next_date_str}",
            }

        workout_confounder = False
        if "workouts" in tables:
            w_row = conn.execute(
                "SELECT SUM(energy_kcal) as kcal FROM workouts WHERE substr(start, 1, 10) = ?",
                (next_date_str,),
            ).fetchone()
            if w_row and w_row["kcal"] and float(w_row["kcal"]) >= 600.0:
                workout_confounder = True
        elif "workout" in tables:
            w_row = conn.execute(
                "SELECT SUM(calorie) as kcal FROM workout WHERE substr(start_utc, 1, 10) = ?",
                (next_date_str,),
            ).fetchone()
            if w_row and w_row["kcal"] and float(w_row["kcal"]) >= 600.0:
                workout_confounder = True

        confounders = dict(manual_confounders)
        if workout_confounder:
            confounders["heavy_training"] = True

    return verify_next_day_rebound(db_path, event_id, next_val, confounders)


def expire_stale_events(db_path: Path, max_age_hours: int = 48) -> int:
    """Transition pending events older than max_age_hours to expired."""
    cutoff_ts = int(time.time()) - (max_age_hours * 3600)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE biometric_rebound_events
            SET status = 'expired'
            WHERE status = 'pending' AND created_ts < ?
            """,
            (cutoff_ts,),
        )
        return cur.rowcount


def generate_report(db_path: Path) -> Dict[str, Any]:
    """Generate stats grouped by intervention type with confounder separation."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT intervention_type, status, subjective_rating, rebound_sigma, rebound_delta_sigma
            FROM biometric_rebound_events
            """
        ).fetchall()

    by_type: Dict[str, Any] = {}
    for r in rows:
        itype = r["intervention_type"]
        if itype not in by_type:
            by_type[itype] = {
                "total": 0,
                "resolved_unconfounded": 0,
                "unresolved": 0,
                "confounded": 0,
                "expired": 0,
                "pending": 0,
                "ratings": [],
                "unconfounded_rebound_sigmas": [],
                "unconfounded_rebound_deltas": [],
            }
        entry = by_type[itype]
        entry["total"] += 1
        status = r["status"]
        if status in ("resolved", "unresolved"):
            if status == "resolved":
                entry["resolved_unconfounded"] += 1
            else:
                entry["unresolved"] += 1
            if r["rebound_sigma"] is not None:
                entry["unconfounded_rebound_sigmas"].append(r["rebound_sigma"])
            if r["rebound_delta_sigma"] is not None:
                entry["unconfounded_rebound_deltas"].append(r["rebound_delta_sigma"])
        elif status == "confounded":
            entry["confounded"] += 1
        elif status == "expired":
            entry["expired"] += 1
        elif status == "pending":
            entry["pending"] += 1

        if r["subjective_rating"] is not None:
            entry["ratings"].append(r["subjective_rating"])

    summary = {}
    for itype, data in by_type.items():
        avg_rating = (
            round(sum(data["ratings"]) / len(data["ratings"]), 2)
            if data["ratings"]
            else None
        )
        avg_rebound = (
            round(
                sum(data["unconfounded_rebound_sigmas"])
                / len(data["unconfounded_rebound_sigmas"]),
                2,
            )
            if data["unconfounded_rebound_sigmas"]
            else None
        )
        avg_delta = (
            round(
                sum(data["unconfounded_rebound_deltas"])
                / len(data["unconfounded_rebound_deltas"]),
                2,
            )
            if data["unconfounded_rebound_deltas"]
            else None
        )
        summary[itype] = {
            "total_events": data["total"],
            "unconfounded_observation_count": data["resolved_unconfounded"] + data["unresolved"],
            "unconfounded_rebound_count": data["resolved_unconfounded"],
            "unresolved_count": data["unresolved"],
            "confounded_count": data["confounded"],
            "expired_count": data["expired"],
            "avg_subjective_rating": avg_rating,
            "avg_unconfounded_rebound_sigma": avg_rebound,
            "avg_unconfounded_rebound_delta_sigma": avg_delta,
        }

    return {"interventions": summary}


def get_verified_hypotheses(
    db_path: Path,
    min_observations: int = 10,
    min_rebound_delta_sigma: float = 1.0,
) -> List[Dict[str, Any]]:
    """Return habit hypotheses that reach N >= 10 unconfounded observations and positive delta."""
    report = generate_report(db_path)
    hypotheses = []
    for itype, stats in report["interventions"].items():
        if stats["unconfounded_observation_count"] >= min_observations:
            avg_delta = stats["avg_unconfounded_rebound_delta_sigma"]
            if avg_delta is not None and avg_delta >= min_rebound_delta_sigma:
                delta_str = f"{avg_delta:+.2f}σ"
                hypotheses.append({
                    "intervention_type": itype,
                    "unconfounded_n": stats["unconfounded_observation_count"],
                    "unconfounded_rebound_count": stats["unconfounded_rebound_count"],
                    "unresolved_count": stats["unresolved_count"],
                    "avg_rebound_delta_sigma": avg_delta,
                    "avg_rebound_sigma": stats["avg_unconfounded_rebound_sigma"],
                    "avg_subjective_rating": stats["avg_subjective_rating"],
                    "epistemic_statement": (
                        f"Associated with {delta_str} recovery delta relative to dip trough "
                        f"under unconfounded conditions (correlated observation; non-causal)."
                    ),
                })
    return hypotheses


def generate_weekly_recap(
    db_path: Path,
    min_observations: int = 10,
    min_rebound_delta_sigma: float = 1.0,
) -> str:
    """Generate a single 1-line somatic recovery recap adhering to minimum sample rules."""
    hypotheses = get_verified_hypotheses(
        db_path,
        min_observations=min_observations,
        min_rebound_delta_sigma=min_rebound_delta_sigma,
    )
    if hypotheses:
        top = sorted(hypotheses, key=lambda h: h["avg_rebound_delta_sigma"], reverse=True)[0]
        name = top["intervention_type"]
        delta = top["avg_rebound_delta_sigma"]
        n = top["unconfounded_n"]
        rebounds = top["unconfounded_rebound_count"]
        sign = "+" if delta >= 0 else ""
        return (
            f"Weekly Somatic Recap: {name} associated with {sign}{delta:.2f}σ recovery rebound "
            f"({rebounds}/{n} recovery rate across {n} unconfounded verified observations)."
        )

    report = generate_report(db_path)
    interventions = report.get("interventions", {})
    if not interventions:
        return "Weekly Somatic Recap: Insufficient unconfounded somatic recovery trials to summarize a trend."

    top_candidate = sorted(
        interventions.items(),
        key=lambda x: (x[1]["unconfounded_observation_count"], x[1]["avg_unconfounded_rebound_delta_sigma"] or -99),
        reverse=True,
    )[0]
    c_name, c_stats = top_candidate
    n_obs = c_stats["unconfounded_observation_count"]
    avg_delta = c_stats["avg_unconfounded_rebound_delta_sigma"]

    if n_obs < min_observations:
        return (
            f"Weekly Somatic Recap: {c_name} recorded {n_obs} unconfounded check-in(s) "
            f"(preliminary; awaiting ≥{min_observations} observations for habit hypothesis promotion)."
        )
    elif avg_delta is not None and avg_delta < min_rebound_delta_sigma:
        sign = "+" if avg_delta >= 0 else ""
        return (
            f"Weekly Somatic Recap: {c_name} reached {n_obs} observations but average rebound delta "
            f"({sign}{avg_delta:.2f}σ) is below promotion threshold (+{min_rebound_delta_sigma:.1f}σ)."
        )

    return "Weekly Somatic Recap: Insufficient unconfounded somatic recovery trials to summarize a trend."


def main():
    db_parent = argparse.ArgumentParser(add_help=False)
    db_parent.add_argument("--db", type=str, default="~/.hermes/data/health.db", help="Path to SQLite health DB")

    parser = argparse.ArgumentParser(description="Biometric recovery and rebound ledger", parents=[db_parent])
    subparsers = parser.add_subparsers(dest="command")

    # Record
    rec_p = subparsers.add_parser("record", parents=[db_parent])
    rec_p.add_argument("--date", type=str, required=True)
    rec_p.add_argument("--metric", type=str, default="nocturnal_rmssd")
    rec_p.add_argument("--baseline-mean", type=float, required=True)
    rec_p.add_argument("--baseline-std", type=float, required=True)
    rec_p.add_argument("--deviation-sigma", type=float, required=True)
    rec_p.add_argument("--intervention-id", type=str, required=True)
    rec_p.add_argument("--intervention-type", type=str, required=True)
    rec_p.add_argument("--cause", type=str)
    rec_p.add_argument("--rating", type=int)

    # Verify
    ver_p = subparsers.add_parser("verify", parents=[db_parent])
    ver_p.add_argument("--event-id", type=str, required=True)
    ver_p.add_argument("--next-rmssd", type=float, required=True)
    ver_p.add_argument("--confounders-json", type=str, help='JSON: {"alcohol": false, "late_meal": true}')

    # Auto-Verify (direct from DB)
    auto_p = subparsers.add_parser("auto-verify", parents=[db_parent])
    auto_p.add_argument("--event-id", type=str, required=True)
    auto_p.add_argument("--confounders-json", type=str, help='Optional JSON manual confounders (e.g. alcohol)')

    # Expire
    exp_p = subparsers.add_parser("expire", parents=[db_parent])
    exp_p.add_argument("--hours", type=int, default=48)

    # Report
    subparsers.add_parser("report", parents=[db_parent])

    # Hypotheses
    hyp_p = subparsers.add_parser("hypotheses", parents=[db_parent])
    hyp_p.add_argument("--min-n", type=int, default=10)
    hyp_p.add_argument("--min-delta", type=float, default=1.0)

    # Recap
    recap_p = subparsers.add_parser("recap", parents=[db_parent])
    recap_p.add_argument("--min-n", type=int, default=10)
    recap_p.add_argument("--min-delta", type=float, default=1.0)

    args = parser.parse_args()
    db_path = Path(args.db).expanduser()

    if args.command == "record":
        eid = record_intervention(
            db_path=db_path,
            date_str=args.date,
            trigger_metric=args.metric,
            baseline_mean=args.baseline_mean,
            baseline_std=args.baseline_std,
            deviation_sigma=args.deviation_sigma,
            intervention_id=args.intervention_id,
            intervention_type=args.intervention_type,
            attributed_cause=args.cause,
            subjective_rating=args.rating,
        )
        print(f"Recorded event: {eid}")
    elif args.command == "verify":
        flags = json.loads(args.confounders_json) if args.confounders_json else {}
        res = verify_next_day_rebound(db_path, args.event_id, args.next_rmssd, flags)
        print(json.dumps(res, indent=2))
    elif args.command == "auto-verify":
        flags = json.loads(args.confounders_json) if args.confounders_json else {}
        res = auto_verify_event(db_path, args.event_id, flags)
        print(json.dumps(res, indent=2))
    elif args.command == "expire":
        n = expire_stale_events(db_path, args.hours)
        print(f"Expired {n} stale pending events.")
    elif args.command == "report":
        print(json.dumps(generate_report(db_path), indent=2))
    elif args.command == "hypotheses":
        print(
            json.dumps(
                get_verified_hypotheses(
                    db_path,
                    min_observations=args.min_n,
                    min_rebound_delta_sigma=args.min_delta,
                ),
                indent=2,
            )
        )
    elif args.command == "recap":
        print(
            generate_weekly_recap(
                db_path,
                min_observations=args.min_n,
                min_rebound_delta_sigma=args.min_delta,
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
