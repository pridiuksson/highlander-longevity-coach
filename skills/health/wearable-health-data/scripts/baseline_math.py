#!/usr/bin/env python3
"""Rolling baseline computation, slope-break detection, and athletic confounder evaluation."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple


def calculate_baseline(values: List[float], min_samples: int = 14) -> Optional[Tuple[float, float]]:
    """Compute baseline mean and sample standard deviation."""
    valid = [float(v) for v in values if v is not None and not math.isnan(v)]
    if len(valid) < min_samples:
        return None
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
    std = math.sqrt(variance)
    return mean, std


def detect_slope_break(
    eval_values: List[float],
    baseline_mean: float,
    baseline_std: float,
    threshold_sigma: float = 1.5,
    lower_is_anomalous: bool = True,
    min_eval_samples: int = 3,
) -> Dict[str, Any]:
    """Detect if the evaluation window mean deviates significantly from the baseline."""
    valid = [float(v) for v in eval_values if v is not None and not math.isnan(v)]
    if len(valid) < min_eval_samples or baseline_std <= 0:
        return {
            "anomaly_detected": False,
            "z_score": 0.0,
            "eval_mean": round(sum(valid) / len(valid), 2) if valid else 0.0,
            "reason": f"Fewer than {min_eval_samples} evaluation samples" if len(valid) < min_eval_samples else "Zero baseline variance",
        }

    eval_mean = sum(valid) / len(valid)
    z_score = (eval_mean - baseline_mean) / baseline_std

    if lower_is_anomalous:
        is_anomaly = z_score <= -threshold_sigma
    else:
        is_anomaly = z_score >= threshold_sigma

    return {
        "anomaly_detected": is_anomaly,
        "z_score": round(z_score, 2),
        "eval_mean": round(eval_mean, 2),
        "baseline_mean": round(baseline_mean, 2),
        "baseline_std": round(baseline_std, 2),
    }


def evaluate_athletic_confounder(
    prior_day_kcal: float,
    prior_day_duration_mins: float,
    baseline_avg_kcal: float = 400.0,
    persistent_dip_days: int = 1,
) -> Dict[str, Any]:
    """Disambiguate athletic exertion from unexplained autonomic stress.

    Uses real features (kcal, duration) rather than vendor strain scores.
    Implements the overtraining carve-out for persistent multi-day dips.
    """
    # Prioritize individual relative baseline multiplier over arbitrary absolute thresholds
    if baseline_avg_kcal > 0:
        is_heavy_session = (
            prior_day_kcal >= 1.5 * baseline_avg_kcal
            or prior_day_duration_mins >= 90.0
        )
    else:
        is_heavy_session = (
            prior_day_kcal >= 600.0
            or prior_day_duration_mins >= 75.0
        )

    if is_heavy_session:
        # Carve-out: persistent dip >= 3 days indicates overtraining, not acute fatigue
        if persistent_dip_days >= 3:
            return {
                "status": "OVERTRAINING_RISK",
                "category": "PHYSICAL_DELOAD",
                "suppress_outreach": False,
                "reason": f"Heavy athletic training with persistent autonomic dip ({persistent_dip_days} days) indicates overtraining.",
            }
        else:
            return {
                "status": "PHYSICAL_LOAD_CONFIRMED",
                "category": "ATHLETIC_RECOVERY",
                "suppress_outreach": True,
                "reason": "Acute autonomic dip explained by prior-day heavy athletic training.",
            }
    else:
        return {
            "status": "UNEXPLAINED_AUTONOMIC_DIP",
            "category": "COGNITIVE_TRIAGE_CANDIDATE",
            "suppress_outreach": False,
            "reason": "Autonomic dip occurred without high athletic load; candidate for cognitive triage.",
        }


def evaluate_biometric_state(
    rmssd_base: List[float],
    rmssd_eval: List[float],
    rhr_base: Optional[List[float]] = None,
    rhr_eval: Optional[List[float]] = None,
    workout_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Full biometric slope-break and confounder analysis."""
    workout_context = workout_context or {}
    rmssd_stats = calculate_baseline(rmssd_base)
    if not rmssd_stats:
        return {
            "status": "INSUFFICIENT_BASELINE",
            "reason": "Fewer than 14 baseline nights available for RMSSD.",
        }

    b_mean, b_std = rmssd_stats
    rmssd_break = detect_slope_break(rmssd_eval, b_mean, b_std, lower_is_anomalous=True)

    rhr_break = None
    if rhr_base and rhr_eval:
        rhr_stats = calculate_baseline(rhr_base)
        if rhr_stats:
            r_mean, r_std = rhr_stats
            rhr_break = detect_slope_break(rhr_eval, r_mean, r_std, lower_is_anomalous=False)

    if not rmssd_break["anomaly_detected"] and not (rhr_break and rhr_break["anomaly_detected"]):
        return {
            "status": "NORMAL_VARIANCE",
            "rmssd": rmssd_break,
            "rhr": rhr_break,
            "suppress_outreach": True,
        }

    # Anomaly detected -> run athletic confounder interlock
    confounder = evaluate_athletic_confounder(
        prior_day_kcal=workout_context.get("prior_day_kcal", 0.0),
        prior_day_duration_mins=workout_context.get("prior_day_duration_mins", 0.0),
        baseline_avg_kcal=workout_context.get("baseline_avg_kcal", 400.0),
        persistent_dip_days=workout_context.get("persistent_dip_days", 1),
    )

    return {
        "status": confounder["status"],
        "category": confounder["category"],
        "suppress_outreach": confounder["suppress_outreach"],
        "reason": confounder["reason"],
        "rmssd": rmssd_break,
        "rhr": rhr_break,
    }


def scan_database(
    db_path: Path,
    target_date_str: str,
    device_source: str = "auto",
) -> Dict[str, Any]:
    """Scan health.db tables to extract 28-day baseline, 7-day evaluation, and workout load."""
    if not db_path.exists():
        return {"status": "ERROR", "reason": f"Database file not found: {db_path}"}

    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }

        # Check if target_dt itself has records (e.g. today's sleep synced), or if latest data is target_dt - 1
        has_target_data = False
        target_str = target_dt.isoformat()
        if "hrv_window" in tables:
            c = conn.execute(
                "SELECT 1 FROM hrv_window WHERE substr(start_utc, 1, 10) = ? LIMIT 1",
                (target_str,),
            ).fetchone()
            if c:
                has_target_data = True
        elif "hrv_sdnn" in tables:
            c = conn.execute(
                "SELECT 1 FROM hrv_sdnn WHERE substr(ts, 1, 10) = ? LIMIT 1",
                (target_str,),
            ).fetchone()
            if c:
                has_target_data = True

        if has_target_data:
            eval_end_date = target_dt
        else:
            eval_end_date = target_dt - timedelta(days=1)

        eval_start = (eval_end_date - timedelta(days=6)).isoformat()
        eval_end = (eval_end_date + timedelta(days=1)).isoformat()
        base_start = (eval_end_date - timedelta(days=34)).isoformat()
        base_end = eval_start
        prior_day = (target_dt - timedelta(days=1)).isoformat()

        # 1. Autonomic metric series (Samsung RMSSD vs Apple SDNN)
        hrv_base: List[float] = []
        hrv_eval: List[float] = []
        metric_name = "unknown"

        if "hrv_window" in tables and device_source in ("auto", "samsung"):
            metric_name = "nocturnal_rmssd"
            rows_base = conn.execute(
                """
                SELECT AVG(rmssd_mean) as val
                FROM hrv_window
                WHERE substr(start_utc, 1, 10) >= ? AND substr(start_utc, 1, 10) < ?
                  AND rmssd_mean > 0 AND rmssd_mean < 250
                GROUP BY substr(start_utc, 1, 10)
                ORDER BY substr(start_utc, 1, 10)
                """,
                (base_start, base_end),
            ).fetchall()
            hrv_base = [r["val"] for r in rows_base if r["val"] is not None]

            rows_eval = conn.execute(
                """
                SELECT AVG(rmssd_mean) as val
                FROM hrv_window
                WHERE substr(start_utc, 1, 10) >= ? AND substr(start_utc, 1, 10) < ?
                  AND rmssd_mean > 0 AND rmssd_mean < 250
                GROUP BY substr(start_utc, 1, 10)
                ORDER BY substr(start_utc, 1, 10)
                """,
                (eval_start, eval_end),
            ).fetchall()
            hrv_eval = [r["val"] for r in rows_eval if r["val"] is not None]

        elif "hrv_sdnn" in tables and device_source in ("auto", "apple"):
            metric_name = "hrv_sdnn"
            rows_base = conn.execute(
                """
                SELECT AVG(value) as val
                FROM hrv_sdnn
                WHERE substr(ts, 1, 10) >= ? AND substr(ts, 1, 10) < ?
                GROUP BY substr(ts, 1, 10)
                ORDER BY substr(ts, 1, 10)
                """,
                (base_start, base_end),
            ).fetchall()
            hrv_base = [r["val"] for r in rows_base if r["val"] is not None]

            rows_eval = conn.execute(
                """
                SELECT AVG(value) as val
                FROM hrv_sdnn
                WHERE substr(ts, 1, 10) >= ? AND substr(ts, 1, 10) < ?
                GROUP BY substr(ts, 1, 10)
                ORDER BY substr(ts, 1, 10)
                """,
                (eval_start, eval_end),
            ).fetchall()
            hrv_eval = [r["val"] for r in rows_eval if r["val"] is not None]

        # 2. Resting Heart Rate series
        rhr_base: List[float] = []
        rhr_eval: List[float] = []
        if "resting_hr" in tables:
            rows_base = conn.execute(
                """
                SELECT AVG(value) as val
                FROM resting_hr
                WHERE substr(date, 1, 10) >= ? AND substr(date, 1, 10) < ?
                GROUP BY substr(date, 1, 10)
                ORDER BY substr(date, 1, 10)
                """,
                (base_start, base_end),
            ).fetchall()
            rhr_base = [r["val"] for r in rows_base if r["val"] is not None]

            rows_eval = conn.execute(
                """
                SELECT AVG(value) as val
                FROM resting_hr
                WHERE substr(date, 1, 10) >= ? AND substr(date, 1, 10) < ?
                GROUP BY substr(date, 1, 10)
                ORDER BY substr(date, 1, 10)
                """,
                (eval_start, eval_end),
            ).fetchall()
            rhr_eval = [r["val"] for r in rows_eval if r["val"] is not None]

        # 3. Workout context
        prior_kcal = 0.0
        prior_duration = 0.0
        base_avg_kcal = 400.0

        if "workouts" in tables:  # Apple schema
            row = conn.execute(
                """
                SELECT SUM(energy_kcal) as kcal, SUM(duration_min) as duration
                FROM workouts
                WHERE substr(start, 1, 10) = ?
                """,
                (prior_day,),
            ).fetchone()
            if row and row["kcal"] is not None:
                prior_kcal = float(row["kcal"])
                prior_duration = float(row["duration"] or 0.0)

            base_row = conn.execute(
                """
                SELECT AVG(daily_kcal) as avg_kcal FROM (
                    SELECT SUM(energy_kcal) as daily_kcal
                    FROM workouts
                    WHERE substr(start, 1, 10) >= ? AND substr(start, 1, 10) < ?
                    GROUP BY substr(start, 1, 10)
                )
                """,
                (base_start, base_end),
            ).fetchone()
            if base_row and base_row["avg_kcal"]:
                base_avg_kcal = float(base_row["avg_kcal"])

        elif "workout" in tables:  # Samsung schema
            row = conn.execute(
                """
                SELECT SUM(calorie) as kcal, SUM(duration_s / 60.0) as duration
                FROM workout
                WHERE substr(start_utc, 1, 10) = ?
                """,
                (prior_day,),
            ).fetchone()
            if row and row["kcal"] is not None:
                prior_kcal = float(row["kcal"])
                prior_duration = float(row["duration"] or 0.0)

            base_row = conn.execute(
                """
                SELECT AVG(daily_kcal) as avg_kcal FROM (
                    SELECT SUM(calorie) as daily_kcal
                    FROM workout
                    WHERE substr(start_utc, 1, 10) >= ? AND substr(start_utc, 1, 10) < ?
                    GROUP BY substr(start_utc, 1, 10)
                )
                """,
                (base_start, base_end),
            ).fetchone()
            if base_row and base_row["avg_kcal"]:
                base_avg_kcal = float(base_row["avg_kcal"])

    finally:
        conn.close()

    # Calculate consecutive trailing dip days in eval window
    persistent_days = 0
    if hrv_base and len(hrv_base) >= 14 and hrv_eval:
        base_mean = sum(hrv_base) / len(hrv_base)
        variance = sum((x - base_mean) ** 2 for x in hrv_base) / (len(hrv_base) - 1)
        base_std = math.sqrt(variance)
        if base_std > 0:
            for val in reversed(hrv_eval):
                if (val - base_mean) / base_std <= -1.5:
                    persistent_days += 1
                else:
                    break

    workout_context = {
        "prior_day_kcal": prior_kcal,
        "prior_day_duration_mins": prior_duration,
        "baseline_avg_kcal": base_avg_kcal,
        "persistent_dip_days": max(1, persistent_days),
    }

    result = evaluate_biometric_state(
        rmssd_base=hrv_base,
        rmssd_eval=hrv_eval,
        rhr_base=rhr_base if rhr_base else None,
        rhr_eval=rhr_eval if rhr_eval else None,
        workout_context=workout_context,
    )
    result["target_date"] = target_date_str
    result["metric_name"] = metric_name
    result["base_samples"] = len(hrv_base)
    result["eval_samples"] = len(hrv_eval)
    return result


def main():
    parser = argparse.ArgumentParser(description="Baseline math and athletic confounder engine")
    parser.add_argument("--db", type=str, help="Path to SQLite health DB for direct table scan")
    parser.add_argument("--date", type=str, help="Target evaluation date (YYYY-MM-DD) for database scan")
    parser.add_argument("--source", type=str, default="auto", choices=["auto", "samsung", "apple"], help="Device source")
    parser.add_argument("--rmssd-base", type=str, help="JSON list of baseline RMSSD readings")
    parser.add_argument("--rmssd-eval", type=str, help="JSON list of evaluation RMSSD readings")
    parser.add_argument("--rhr-base", type=str, help="Optional JSON list of baseline RHR readings")
    parser.add_argument("--rhr-eval", type=str, help="Optional JSON list of evaluation RHR readings")
    parser.add_argument("--workout-kcal", type=float, default=0.0, help="Prior day workout active kcal")
    parser.add_argument("--workout-duration", type=float, default=0.0, help="Prior day workout duration in minutes")
    parser.add_argument("--persistent-days", type=int, default=1, help="Consecutive days of autonomic dip")
    parser.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args()

    if args.db and args.date:
        res = scan_database(Path(args.db).expanduser(), args.date, device_source=args.source)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Target Date: {res.get('target_date')}")
            print(f"Metric: {res.get('metric_name')}")
            print(f"Status: {res['status']}")
            print(f"Category: {res.get('category', 'N/A')}")
            print(f"Suppress Outreach: {res.get('suppress_outreach', True)}")
            print(f"Reason: {res.get('reason', 'N/A')}")
        sys.exit(0)

    if not args.rmssd_base or not args.rmssd_eval:
        parser.print_help()
        sys.exit(1)

    rmssd_base = json.loads(args.rmssd_base)
    rmssd_eval = json.loads(args.rmssd_eval)
    rhr_base = json.loads(args.rhr_base) if args.rhr_base else None
    rhr_eval = json.loads(args.rhr_eval) if args.rhr_eval else None

    workout_context = {
        "prior_day_kcal": args.workout_kcal,
        "prior_day_duration_mins": args.workout_duration,
        "persistent_dip_days": args.persistent_days,
    }

    result = evaluate_biometric_state(
        rmssd_base, rmssd_eval, rhr_base=rhr_base, rhr_eval=rhr_eval, workout_context=workout_context
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Status: {result['status']}")
        print(f"Category: {result.get('category', 'N/A')}")
        print(f"Suppress Outreach: {result.get('suppress_outreach', True)}")
        print(f"Reason: {result.get('reason', 'N/A')}")


if __name__ == "__main__":
    main()
