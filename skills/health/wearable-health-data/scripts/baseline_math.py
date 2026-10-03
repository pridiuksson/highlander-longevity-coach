#!/usr/bin/env python3
"""Rolling baseline computation, slope-break detection, and athletic confounder evaluation."""
from __future__ import annotations
import argparse
import json
import math
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


def main():
    parser = argparse.ArgumentParser(description="Baseline math and athletic confounder engine")
    parser.add_argument("--rmssd-base", type=str, help="JSON list of baseline RMSSD readings")
    parser.add_argument("--rmssd-eval", type=str, help="JSON list of evaluation RMSSD readings")
    parser.add_argument("--rhr-base", type=str, help="Optional JSON list of baseline RHR readings")
    parser.add_argument("--rhr-eval", type=str, help="Optional JSON list of evaluation RHR readings")
    parser.add_argument("--workout-kcal", type=float, default=0.0, help="Prior day workout active kcal")
    parser.add_argument("--workout-duration", type=float, default=0.0, help="Prior day workout duration in minutes")
    parser.add_argument("--persistent-days", type=int, default=1, help="Consecutive days of autonomic dip")
    parser.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args()

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
