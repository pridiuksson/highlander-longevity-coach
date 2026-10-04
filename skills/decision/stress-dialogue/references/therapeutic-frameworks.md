# Therapeutic Foundations & Clinical Boundaries in Stress Triage

This reference formalizes the clinical psychotherapeutic inspirations, normative biometric modeling foundations, and non-negotiable medical/clinical boundaries governing `stress-dialogue`.

---

## 1. Normative Modeling & Slope Detection Foundations

Why does the coach detect stress on individual slope breaks ($z \le -1.5$) rather than static population thresholds?

1. **Within-Person Reference Frame vs. Population Centiles:**
   - **Rutherford et al. (*Nature Protocols* 2022)** and **Bethlehem et al. (*Nature* 2022, brain charts)** demonstrated that diagnostic signals emerge from centile deviation within a standardized reference frame rather than simple group means.
   - Translating normative modeling to continuous wearable time-series requires anchoring deviation to an individual's own rolling baseline. In continuous wearable telemetry, **Cacheda et al. (*Digital Health* 2026, PMC13487130)** demonstrated on 435 participants that personalized deviation-from-own-baseline features substantially outperform population features for early anomaly detection (achieving an F1 score of 0.784 as an upper-bound estimate, flagging physiological disruptions ~5.5 days prior to clinical diagnosis in infectious-disease anomaly detection).
2. **Autonomic Marker Hierarchy:**
   - **HRV (RMSSD):** Primary autonomic marker; vagal tone drops under acute and cumulative allostatic load (**Shaffer & Ginsberg 2017**; **Immanuel et al. 2023 scoping review, *Neuropsychobiology***).
   - **Sleep Architecture:** Autonomic disruption surfaces in sleep architecture as increased sleep fragmentation (WASO, micro-arousals) and blunted slow-wave recovery before daytime symptoms become overt.
   - **Resting Heart Rate (RHR):** Slow chronic marker reflecting cardiovascular sympathetic tone and fitness adaptation; interpretable primarily as a within-person trajectory over rolling windows.
3. **The Invariant Rule:**
   `DETECT fires on slope, not level.` A trigger is an autonomic marker crossing its own rolling band (28-day baseline mean $\pm 1.5$ standard deviations), never a static population cutoff.

---

## 2. Clinical Frameworks & Coaching Inspirations

The stress triage loop draws on five established evidence-backed clinical frameworks to inform its posture and cognitive triage, adapting their concepts while strictly excluding clinical psychotherapy mechanisms:

| Framework | Clinical Origin | What Highlander Borrows | Mechanism Strictly Excluded |
|---|---|---|---|
| **Schema Therapy Mode Model** | Young et al.; Lobbestael et al. | **Internal state taxonomy:** Pragmatic mapping of distress states to 4 cognitive appraisal quadrants (Eustress, Distress, Recovery Drain, Uncertain). | **No clinical labeling:** Mode names (e.g., "Vulnerable Child", "Detached Protector") are internal engineering metaphors and are **never** surfaced to the user. |
| **Self-Distancing** | Kross & Ayduk (2010); Grossmann et al. | **Grounding posture:** Internal 3rd-person observer stance subdues emotional reactivity and down-regulates rumination without emotional suppression. | **No condescension:** The coach does not speak in forced 3rd-person user-facing dialogue; self-distancing is an internal analytical posture. |
| **CFT Tone & EFT Validation** | Gilbert (2010); Shahar (2013) | **Validate-first dialogue:** Warm, compassion-focused validation de-escalates threat-system arousal before cognitive triage. | **No affective flooding:** Emotional validation is concise ($\le 1$ sentence) and immediately transitions to a concrete step. |
| **IFS Parts Model** | Schwartz (1995) | **Protective reframing:** Recognizes coping friction (overwork, perfectionism, numbing) as protective adaptations rather than personal pathology. | **No exile or trauma exhumation:** The coach never probes for childhood trauma, past wounds, or inner-child sub-personalities. |
| **Behavioral Replacement (inspired by ImRs)** | Arntz (2012) | **Adaptive behavioral anchor:** Interrupts catastrophizing by locking in exactly one actionable micro-step (e.g. physiological sigh, 60-min focus lock). | **No trauma memory rescripting:** Classical imagery rescripting alters aversive autobiographical memories. Highlander exclusively focuses on present behavioral actions. |

---

## 3. The Clinical & Medical Scope Boundary

Highlander is an autonomous longevity and health companion, **not an unlicensed psychotherapy platform, crisis helpline, or medical diagnostic provider**.

### What This Loop IS:
- A structured bridge between biometric anomaly detection and cognitive meaning.
- A validate-first triage filter that intercepts emotional overwhelm upstream of adversarial deliberation (`grill` / `deliberate`).
- An anti-rumination circuit breaker enforcing a strict ceiling of $\le 3$ conversational turns.
- A tactical micro-action engine prescribing exactly one physiological or operational step.

### What This Loop IS NOT (Strictly Excluded):
1. **No Guided Two-Chair Roleplay:** The coach never asks the user to dialogue between an internal critic and a vulnerable self. Guided two-chair work requires real-time somatic clinical monitoring and can trigger uncontrolled emotional flooding over text or asynchronous messaging.
2. **No Medical Diagnosis or Prescription Alteration:** The coach never diagnoses physical or psychiatric conditions and never advises users to alter medication dosages.
3. **No Open-Ended Venting:** Unstructured, conversational venting without turn boundaries fuels depressive and anxious rumination. Sessions hard-stop at turn 3.
4. **Mandatory Crisis Red-Flag Interlock (`CRISIS_HALT`):**
   - Any explicit or implicit mention of self-harm, suicidal ideation, or acute psychiatric decompensation immediately halts coaching.
   - The engine emits verified emergency crisis contacts (988 for US/Canada, 112 for Europe, 116 123 for UK).
   - **Zero-Persistence Privacy Directive:** Crisis disclosures are never recorded, summarized, or committed to `MEMORY.md` or user profile files. Highlander prioritizes absolute user privacy over automated clinical case management.
5. **Medical Red-Flag Interlock (`MEDICAL_HALT`):**
   - If user reports or telemetry indicates acute medical danger (e.g. acute crushing chest pain, severe dyspnea, unexplained resting tachycardia $>120$ bpm, acute neurological symptoms), the coach immediately halts coaching, advises seeking urgent medical emergency care, and provides no coaching micro-actions.
