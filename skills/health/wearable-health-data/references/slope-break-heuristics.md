# Slope-Break Detection & Athletic Load Disambiguation

This document formalizes the mathematics for detecting biometric slope breaks and disambiguating athletic exertion from unexplained autonomic stress.

## 1. The Slope-Not-Level Rule

Wearable metrics must be compared against the individual's own rolling baseline, never against generic population averages (Marquand et al., *Nature Protocols* 2022).

- **Baseline Window ($W_{\text{base}}$):** Non-overlapping 28-day historical window. Requires at least 14 valid nightly readings.
- **Evaluation Window ($W_{\text{eval}}$):** 7-day trailing window.
- **Slope-Break Threshold:** The 7-day mean deviates from the baseline mean by $\ge 1.5\sigma$:
  $$z = \frac{\mu_{\text{eval}} - \mu_{\text{base}}}{\sigma_{\text{base}}}$$
- **Negative Directionality:**
  - Nocturnal HRV (RMSSD autonomic series): normalized score deviation $z \le -1.5$ (vagal withdrawal)
  - Resting Heart Rate: normalized score deviation $z \ge +1.5$ (sympathetic elevation / cardiovascular strain)
  - Sleep Fragmentation (WASO / awakenings): normalized score deviation $z \ge +1.5$ (autonomic arousal during sleep)

## 2. Multi-Device Metric Partitioning

Do **not** blend metrics across device boundaries or firmware eras without normalization:
- **Samsung Health:** Nocturnal RMSSD from hourly `hrv_window`, resting HR proxy from `min_hr`.
- **Garmin:** Daily summary `resting_hr` and FIT `rhr_snapshot`. (Older Garmins such as Fenix 3 HR have no RMSSD).
- **Apple Health:** Reports SDNN, not RMSSD. Must be kept in a distinct series.

## 3. Athletic Load Disambiguation (The Confounder Filter)

A drop in nocturnal HRV or spike in resting HR is often the normal, expected biological response to hard physical training.

### Verified Load Features (Existing Schema)
Rather than ungrounded vendor scores (e.g. Whoop 0–21 strain), load must be derived from verified physical metrics in `$HERMES_HOME/data/health.db` or `$HERMES_HOME/data/garmin.db`:
- **Workout Active Caloric Expenditure ($E_{\text{kcal}}$):** FIT-arbitrated active kcal $> 600$ kcal.
- **Session Duration:** Moderate-to-high intensity endurance or resistance training $> 75$ minutes.
- **Relative Load Jump:** Prior-day training load $> 1.5\times$ the 28-day rolling daily average.

### Attribution Rules
1. **Physical Adaptation:** If an acute autonomic dip ($z \le -1.5\sigma$) occurs immediately following a documented heavy workout, tag as `PHYSICAL_LOAD_CONFIRMED`. Proactive mental stress check-ins are suppressed.
2. **The Overtraining Carve-Out:** If autonomic depression persists for **$\ge 3$ consecutive days** despite reduced training, or if all three markers (RMSSD $\downarrow$, RHR $\uparrow$, Sleep Fragmentation $\uparrow$) are concordant, do **not** suppress. Route to the `Protector` profile for mandatory physical deload coaching.
3. **Unexplained Autonomic Dip:** If an autonomic dip occurs with normal or low athletic load ($<1.0\times$ daily average), tag as `UNEXPLAINED_AUTONOMIC_DIP`. This candidate is routed to `stress-dialogue` triage.
