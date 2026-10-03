---
name: biometric-recovery-ledger
description: "Closed-loop somatic recovery ledger that tracks biometric rebounds and filters lifestyle confounders."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, darwin]
metadata:
  hermes:
    config:
      - key: health.db
        description: "SQLite database holding the imported, normalized device data and somatic events"
        default: "${HERMES_HOME}/data/health.db"
        prompt: "SQLite database holding the imported, normalized device data and somatic events"
      - key: stress.min_hypothesis_n
        description: "Minimum unconfounded observations required before promoting a habit hypothesis"
        default: "10"
        prompt: "Minimum unconfounded observations required before promoting a habit hypothesis"
    tags: [health, recovery, ledger, verification, closed-loop]
---

# Biometric Recovery Ledger

Closes the empirical coaching loop by evaluating whether physiological anomalies (such as nocturnal RMSSD dips) rebound on subsequent nights following coaching micro-actions, while strictly isolating macroscopic lifestyle confounders.

## Why This is Isolated from `proactive-coach`

Highlander's proactive coach ledger (`proactive-coach/scripts/ledger.py`) manages **communication interruption policy** (`acted|ignored|corrected|dropped`) and computes schedule shifts (`shift_earlier`, `cooldown`).

Overloading that communication ledger with nocturnal biological metrics causes domain and timing mismatches:
- Compliance with advice (`acted`) does not guarantee biological rebound if heavy physical exertion or alcohol intervened.
- Biological state transitions belong in somatic health data (`health.db`), not in notification dispatch logs.

## Confounder Exclusion Gating

Macro-shocks completely overwhelm micro-intervention signals:
- Alcohol consumption ($-20\%\text{ to }-40\%$ nocturnal RMSSD)
- Late meals within 3 hours of sleep ($-10\%\text{ to }-25\%$)
- Bedtime drift $>1.5$ hours
- Heavy athletic training load

A next-day rebound is only scored as `resolved` when all confounder flags evaluate to `False`. If any confounder is present, the event is marked `confounded` and excluded from habit aggregation.

## Pointer Memory Architecture

1. **Storage on Disk:** All observations live in SQLite (`biometric_rebound_events`). They are never auto-written into `MEMORY.md`.
2. **Epistemic Modesty:** Rebounds are labeled as **correlated observations, never causal proof**. Regression to the mean is explicitly accounted for.
3. **Hypothesis Promotion:** Only when an intervention reaches $N \ge 10$ unconfounded observations across multiple weeks is a candidate surfaced to the user during longitudinal review (`eval-health`), requiring human confirmation before entering durable memory.

See `references/confounder-exclusion-rules.md` for complete mathematical and statistical derivations.

## Execution

Record an intervention event:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/rebound_tracker.py record \
  --db ${health.db} \
  --date 2026-10-03 \
  --metric nocturnal_rmssd \
  --baseline-mean 60.0 \
  --baseline-std 5.0 \
  --deviation-sigma -1.8 \
  --intervention-id act_sigh_01 \
  --intervention-type physiological_sigh \
  --cause "deadline_crunch" \
  --rating 4
```

Verify subsequent night rebound (manual values):

```bash
python3 ${HERMES_SKILL_DIR}/scripts/rebound_tracker.py verify \
  --db ${health.db} \
  --event-id <EVENT_ID> \
  --next-rmssd <VALUE> \
  --confounders-json '{"alcohol": false, "late_meal": false}'
```

Automatically verify subsequent night rebound directly from database telemetry:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/rebound_tracker.py auto-verify \
  --db ${health.db} \
  --event-id <EVENT_ID> \
  --confounders-json '{"alcohol": false, "late_meal": false}'
```

Generate recovery report:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/rebound_tracker.py report --db ${health.db}
```

Audit verified habit hypotheses ($N \ge 10$ unconfounded observations with $\Delta\sigma \ge +1.0$):

```bash
python3 ${HERMES_SKILL_DIR}/scripts/rebound_tracker.py hypotheses \
  --db ${health.db} \
  --min-n 10 \
  --min-delta 1.0
```
