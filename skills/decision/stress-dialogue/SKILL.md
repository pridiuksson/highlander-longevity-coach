---
name: stress-dialogue
description: "Pre-Decide cognitive appraisal triage and anti-rumination check-in when stress or autonomic anomalies are flagged."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, darwin]
metadata:
  hermes:
    config:
      - key: stress.max_turns
        description: "Hard cap on conversational turns to prevent emotional rumination"
        default: "3"
        prompt: "Hard cap on conversational turns to prevent emotional rumination"
      - key: stress.quiet_hours
        description: "Allowed window for proactive check-in delivery"
        default: "08:00-21:00"
        prompt: "Allowed window for proactive check-in delivery"
      - key: stress.crisis_contact
        description: "Local crisis resources provided if acute distress is detected"
        default: "988 (US/Canada), 112 (Europe), 116 123 (UK)"
        prompt: "Local crisis resources provided if acute distress is detected"
    tags: [stress, cognitive-appraisal, triage, decision, mental-health-first-aid]
---

# Stress Dialogue & Cognitive Appraisal Triage

Connects wearable autonomic anomalies and subjective user overwhelm to meaning, using a validate-first posture, silent 3rd-person observer distancing, and 4-quadrant cognitive appraisal triage.

## Why This is Pre-Decide

In Highlander, the `Decide` stage (`peer-review → grill → deliberate`) runs adversarial debate and expert cross-examinations. **Adversarial debate is precisely the wrong machinery for an emotionally flooded or exhausted user.**

This skill acts as an early triage filter ahead of `Decide`:
- If an issue is an emotional, interpersonal, or acute stress friction, route into `stress-dialogue`.
- Do not route flooded emotional sharing into `deliberate` or `grill`.

## Core Invariants

1. **Mandatory Crisis Red-Flag Interlock:**
   The coach is a longevity companion, not a therapist or crisis counselor. Any mention of self-harm, suicidal ideation, or acute psychiatric decompensation immediately halts the coaching loop and emits emergency hotline contacts (`stress.crisis_contact`).
2. **Validate First, Ground Second:**
   Under emotional flooding, immediate cognitive reappraisal feels dismissive. The coach always opens with warm first-person validation before stepping into a calm, silent observer perspective.
3. **Physiology-First Disambiguation:**
   Wearable telemetry arbitrates state. If sleep fragmentation is high or RMSSD has been suppressed for multiple days, the state is categorized as **Recovery Drain** (physical deficit), regardless of whether the user attempts to rationalize it as a purely psychological issue.
4. **Anti-Rumination Circuit Breaker (≤3 Turns):**
   Conversations are strictly capped at `stress.max_turns` (default: 3 turns). If the user begins circular venting, the agent grounds the user and exits.
5. **Exactly ONE Tactical Micro-Action:**
   The dialogue always concludes with a single, immediate behavioral micro-action (physiological sigh, 60-minute focus boundary, early sleep window, or 5-minute grounding walk). Never deliver a list of suggestions.
6. **CRITICAL PRIVACY DIRECTIVE — Zero Long-Term Memory Persistence on Crisis:**
   Upon triggering `CRISIS_HALT`, emit the crisis emergency message and immediately terminate the turn. Do NOT write, append, or summarize this turn to `MEMORY.md`, daily journals, or any profile storage.

## Appraisal Quadrants

| Quadrant | Valence & Control | Primary Intervention |
|---|---|---|
| **Eustress** | High Control, Challenge | 60-Minute Focus Boundary; defend deep work |
| **Distress** | Low Control, Threat | Cyclic Physiological Sighing (5 reps); down-regulation |
| **Recovery Drain** | Low Control, Depleted | Early Sleep Window; training deload; zero guilt |
| **Uncertain** | Ambiguous Context | 5-Minute Grounding Walk / Water Pause |

See `references/cognitive-appraisal-taxonomy.md` for full taxonomy and clinical grounding.

## Execution

Evaluate context or run triage headlessly:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/dialogue_triage.py --text "I am panicking about this deadline" --json
```

Or check crisis safety standalone:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/dialogue_triage.py --crisis-check "feeling overwhelmed"
```
