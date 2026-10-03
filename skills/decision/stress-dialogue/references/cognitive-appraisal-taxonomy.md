# Cognitive Appraisal & Stress Triage Taxonomy

This reference formalizes the cognitive appraisal triage model implemented in `stress-dialogue`. It bridges wearable physiological signals and subjective psychological self-reports, providing structured triage without engaging in clinical psychotherapy.

## Theoretical Foundations

1. **Transactional Model of Stress & Coping (Lazarus & Folkman 1984):** Stress is not an environmental stimulus or physiological response alone, but the relationship between the person and the environment, mediated by cognitive appraisal:
   - *Primary Appraisal:* Is this event irrelevant, benign-positive, or stressful (harm/loss, threat, or challenge)?
   - *Secondary Appraisal:* What coping options and resources are available (perceived control)?
2. **Physiology-First Disambiguation Rule:** When subjective narrative and wearable telemetry diverge, wearable telemetry arbitrates physiological state. A person claiming "I'm just mentally stressed" who exhibits acute sleep fragmentation and multi-day HRV depression after heavy exertion is experiencing physiological recovery drain, not a pure mindset problem.
3. **Self-Distancing & Affect Regulation (Kross & Ayduk 2010; Moser et al. 2017):** Stepping back into an observer perspective reduces emotional reactivity and rumination. In this skill, self-distancing is an internal coaching posture (silent 3rd-person analysis) to avoid condescending user-facing prose.
4. **Compassion-Focused Triage (Gilbert 2010):** De-escalates threat-system arousal through warmth and validation before offering tactical behavioral micro-actions.

---

## The 4 Appraisal Quadrants

| Quadrant | Perceived Control | Emotional Valence | Telemetry Signature | Coaching Micro-Action |
|---|---|---|---|---|
| **Eustress** (Challenge) | High | Positive / Neutral | Autonomic activation without sleep fragmentation | Defend deep focus, protect boundaries against overcommitment |
| **Distress** (Threat) | Low / Impaired | Negative / Anxious | Autonomic dip without physical workout load | Down-regulate nervous system (cyclic sigh, sensory grounding) |
| **Recovery Drain** (Deficit) | Low / Depleted | Fatigue / Numb | Multi-night sleep fragmentation, blunted RMSSD, RHR drift | Deload training, enforce early sleep window, eliminate guilt |
| **Uncertain** (Ambiguous) | Undetermined | Mixed / Unclear | Baseline variance within normal range | Ask 1 targeted clarifying question; default to down-regulation |

---

## Safety Guardrails & Crisis Interlock

The coach is an autonomous health and longevity companion, **not a crisis helpline or mental health clinician**.

### Red-Flag Criteria
If any user input matches explicit or implicit indicators of:
- Suicidal ideation, suicidal intent, or hopelessness (*"want to end it"*, *"better off dead"*, *"can't go on"*, *"suicide"*)
- Self-harm urges or actions (*"hurt myself"*, *"cutting"*)
- Acute psychotic decompensation or severe psychiatric crisis

### Mandatory Interlock Behavior
1. **Immediate Loop Termination:** Halt the dialogue triage loop immediately. Never ask clarifying questions, explore root causes, or suggest breathing exercises.
2. **Direct Referral Emission:** Emit a warm, non-judgmental crisis message providing verified national/international crisis resources configured in `stress.crisis_contact`.
3. **No Memory Recording:** Never persist crisis disclosures into `MEMORY.md` or searchable user profile files.
