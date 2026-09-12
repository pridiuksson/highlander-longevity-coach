# Consumer Wearable Data — Reliability Guide

*Created 2026-06-28 after session where deep-sleep optimization protocol was built and retracted based on unreliable Samsung Galaxy Watch 7 stage data.*

## Device: Samsung Galaxy Watch 7

### Trust as TREND indicators (relative changes over time)
- **Heart rate** (resting, sleeping, exercise) — optical sensor is decent. Use for trends.
- **HRV** (heart rate variability) — relative trends meaningful. Absolute values vary by algorithm.
- **Total sleep time** — typically ±10–15 min of reality.
- **Sleep/wake timestamps** — objective clock times, reliable.
- **Step count** — good enough for activity-level categorization.
- **VO2max estimate** — trend direction reliable (decline vs improvement). Absolute value approximate (±3–5 ml/kg/min vs lab test).

### Do NOT trust as OPTIMIZATION TARGETS (accuracy insufficient for protocol-building)
- **Deep sleep vs light sleep split** — wearables estimate stages from accelerometer + HRV + skin temp. Agreement with polysomnography (EEG gold standard): 50–70%. Routinely confuse motionless light sleep with deep sleep.
- **REM estimation** — similar accuracy issues as deep sleep.
- **Sleep latency** — detects "no movement" but not "awake in bed." Can't distinguish lying still from sleeping.
- **Body composition (BIA)** — bioelectrical impedance. Hydration status shifts readings several kg. Creatine supplementation inflates lean mass via intracellular water. Use for yearly trends only, never individual data points.
- **Skin temperature** — relative to baseline, not absolute. Useful for spotting illness or menstrual cycle patterns. Not reliable enough to build temperature-based sleep protocols.

### Lessons from 2026-06-28 session
1. An entire deep-sleep optimization protocol (bedroom temp, hot shower timing) was built from watch deep-sleep data (40–90 min range). The user corrected: "treat this as soft data." Protocol was retracted.
2. A skin-temperature theory was proposed (warmer skin = worse deep sleep via core temp). Actual data showed the OPPOSITE (warmer skin night had BETTER deep sleep). Theory was retracted. Root cause: building theories on data too soft to support them.
3. Individual-night deep sleep readings (40, 84, 90 min) caused assessment flip-flopping ("broken" → "elite"). The yearly average (62 min = average, not broken, not elite) was the signal. Individual readings were noise.

### Rule of thumb
**If an optimization protocol depends on the PRECISION of a single wearable metric (not the trend), it's over-engineered.** Wearables answer "is this getting better or worse over weeks?" not "was last night's deep sleep 40 or 60 minutes?" Build protocols around outcome metrics (HR, HRV, performance, energy) not stage-level estimations.
