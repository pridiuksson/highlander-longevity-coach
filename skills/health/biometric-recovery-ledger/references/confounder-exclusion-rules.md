# Confounder Exclusion & Epistemic Modesty Rules

This document defines the mathematical and statistical rules for scoring biometric rebound following coaching interventions in `biometric-recovery-ledger`.

## 1. The Signal-to-Noise Ratio (SNR) Reality

An acute behavioral or psychological intervention (e.g. 5-minute physiological sighing, boundary clarification, task prioritization) creates transient vagal activation lasting 15 to 45 minutes.

Its residual autonomic signature 10 to 14 hours later during nocturnal slow-wave sleep is subtle ($<0.1\sigma$). In contrast, macroscopic lifestyle shocks produce massive autonomic disturbances:

| Lifestyle Confounder | Typical Nocturnal RMSSD Impact | Mechanism |
|---|---|---|
| **Alcohol Consumption** | $-20\%\text{ to }-40\%$ suppression | Hepatic acetaldehyde clearance drives sustained sympathetic tachycardia throughout first 4–6 hours of sleep. |
| **Late Dinner ($<3\text{h}$ before bed)** | $-10\%\text{ to }-25\%$ suppression | Diet-induced thermogenesis elevates core body temperature and metabolic rate, delaying parasympathetic dominance. |
| **Bedtime Shift ($>1.5\text{h}$ drift)** | $-10\%\text{ to }-20\%$ suppression | Circadian autonomic desynchronization. |
| **Heavy Eccentric Muscle Damage** | Multi-day $-15\%\text{ to }-30\%$ depression | Systemic inflammatory cytokines (IL-6, TNF-alpha) blunt vagal reactivation. |

## 2. Confounder Exclusion Gating

To prevent the coach from attributing biological recovery to an afternoon breathing drill when macroscopic confounders are present, the verification pass enforces strict exclusion:

```
IF alcohol == True               -> status = 'confounded'
IF late_meal == True             -> status = 'confounded'
IF bedtime_drift > 1.5h          -> status = 'confounded'
IF heavy_athletic_load == True   -> status = 'confounded'
ELSE                             -> status = 'resolved'
```

A rebound is scored as a valid observational candidate **only** when all confounder flags evaluate to `False`.

## 3. Epistemic Modesty & Galton's Fallacy

An extreme negative outlier (e.g. $z = -2.0\sigma$) naturally regresses toward the mean on subsequent nights due to basic autoregressive properties of biological time series:
$$X_{t+1} = \mu + \phi (X_t - \mu) + \epsilon_t \quad (0 < \phi < 1)$$

Attributing next-day recovery to a micro-action without accounting for regression to the mean is a post-hoc fallacy.

### Reporting Taxonomy
1. **Decoupled Scoring:** Subjective rating ($1\text{ to }5$) and objective biometric delta ($\Delta\sigma$) are stored as independent fields. An intervention can be subjectively helpful ($5/5$) even if physiology does not rebound, and vice versa.
2. **Correlated Observation:** Any summary produced by this system must describe rebounds as:
   `"Metric normalized toward personal baseline (correlated observation; non-causal)"`
3. **Pointer Memory Rule:** Observations remain in SQLite storage on disk. Hypotheses are only promoted to user-facing reviews when $N \ge 10$ unconfounded observations exist across at least 8 distinct weeks, confirmed by human testimony per `memory-reality-check`.
