# Profile templates

A skill set is not a coach. The coaching **loop** lives in three files the agent reads every
turn, and this folder ships eight canonical psychological personas alongside modular clinical scaffolds.

## Two-Tier Architecture

To avoid conflating the AI's communication stance with human physiological traits, Highlander separates
coaching configuration into two composable tiers:

1. **Tier 1: Canonical `SOUL.md` Personas (The AI's Mind)** — Governs communication cadence, pushback,
   decision authority, pedagogical posture, and cognitive boundaries.
2. **Tier 2: Modular `USER.md` Scaffolds (The Human's Biology)** — Governs endocrine status, biomarker kinetics,
   cardiovascular targets, and training splits. Found in [`scaffolds/`](./scaffolds/).

---

## 10-Second Quick Triage Tree

Find your matching coaching persona in seconds by answering one question: **What is your primary coaching need right now?**

```
What is your primary coaching need?
│
├── 🚀 I want to build momentum, expand physical capacity, and optimize vitality
│   ├── "Fire me up, help me build streaks, and give me immediate daily action." → Catalyst
│   └── "Connect my training to lifelong vitality, cognitive health, and a 50-year horizon." → Visionary
│
├── ⚡ I want rigorous truth, high efficiency, and zero fluff
│   ├── "Spar with me, push back on assumptions, and verify data independently." → Operator
│   ├── "Show me the clinical trial evidence, effect sizes, and raw biomarker trends." → Scholar
│   └── "Give me 2–3 compact takeaways on mobile; no essays, single questions only." → Concise
│
└── 🛡️ I want guidance, habit restoration, or nervous system balance
    ├── "Offload decision fatigue, explain the 'why', and absorb the planning QA burden." → Guide
    ├── "Rebuild consistency after injury/burnout with zero guilt and micro-habits." → Rebuilder
    └── "De-escalate wearable anxiety (orthosomnia/CGMs) and enforce recovery deloads." → Protector
```

---

## The 8 Canonical Personas

| Template | Persona | Core Posture | Best Suited To |
|---|---|---|---|
| [`Catalyst/`](./Catalyst/) | **Action Coach** | High-energy, positive spark; ends every turn with $\ge 1$ immediate action; dopamine kinetics. | Strivers seeking athletic momentum, streak-building, and an enthusiastic partner who says "YES" to ambition. |
| [`Visionary/`](./Visionary/) | **Vitality Architect** | 50-year horizon, salutogenesis, centenarian decathlon; connects habits to lifelong flourishing. | Creators, leaders, and long-term planners optimizing for functional independence and multi-decade vitality. |
| [`Operator/`](./Operator/) | **Autonomous Challenger** | Direct, unpadded pushback; strict pre-flight verification gate; asymmetric mistake rule. | High-agency operators and executives who want an unhedged sparring partner holding them accountable. |
| [`Scholar/`](./Scholar/) | **Clinical Scientist** | Evidence-first ("number before narrative"); inspects raw tables/APIs; strict evidence hierarchy. | Clinicians, researchers, engineers, and biohackers who demand PubMed RCT effect sizes and zero marketing fluff. |
| [`Guide/`](./Guide/) | **Executive Concierge** | Warm, consultative educator; explains the *why*; single clear recommendations; absorbs QA burden. | Domain experts and professionals who want high-leverage health offloading without needing to be an AI/prompt wizard. |
| [`Concise/`](./Concise/) | **Mobile Minimalist** | Ultra-compact (2–3 paragraphs max), 1 question at a time, micro-actions, zero cognitive fatigue. | Time-starved executives, mobile chat users (Telegram/WhatsApp/Signal), or anyone overwhelmed by long essays. |
| [`Rebuilder/`](./Rebuilder/) | **Habit Scaffolder** | Radical psychological safety, zero judgment/guilt, graded behavioral activation (micro-wins). | Beginners, detrained individuals, or those recovering from burnout/injury; includes 60-day graduation path. |
| [`Protector/`](./Protector/) | **Down-Regulator** | Calming stoicism; anti-orthosomnia and CGM panic protocols; mandatory deload enforcer. | Anxious over-optimizers and quantified-self users trapped in biometric hyper-vigilance or sympathetic exhaustion. |

---

## Modular Physiological & Clinical Scaffolds (`scaffolds/`)

To specialize your profile for your biological stage and performance goals, drop one or more scaffolds from [`scaffolds/`](./scaffolds/)
into your `USER.md` under `# Health and training`.

Every scaffold implements Highlander's **Two-Layer Architecture**:
1. **Vitality Ceiling (Medicine 3.0)** — Proactive salutogenesis, mitochondrial bioenergetics, cognitive neuroplasticity, athletic reserve surplus, and cycle autoregulation.
2. **Clinical Floor (Medicine 2.0)** — Safety contraindications, diagnostic thresholds, red flags, biomarker surveillance, and single-lab repeat rules.

| Scaffold | Vitality Ceiling (Salutogenesis) | Clinical Floor (Safety & Triage) | Landmark SoT / PMIDs |
|---|---|---|---|
| [`USER_mitochondrial_vitality.md`](./scaffolds/USER_mitochondrial_vitality.md) | PGC-1alpha reticular biogenesis, Zone 2 lactate clearance, GLUT4 non-insulin glucose flux. | Fasting insulin floor ($<5$ mcIU/mL), HOMA-IR $<1.2$, uric acid $<5.0-5.5$ mg/dL (eNOS defense). | San-Millan & Brooks 2018 ([PMID: 28623351](https://pubmed.ncbi.nlm.nih.gov/28623351)), Hood 2019 ([PMID: 30896359](https://pubmed.ncbi.nlm.nih.gov/30896359)) |
| [`USER_cognitive_neurolongevity.md`](./scaffolds/USER_cognitive_neurolongevity.md) | Exercise BDNF hippocampal neurogenesis, N3 slow-wave glymphatic wash, vagal tone (PFC regulation). | hs-CRP $<0.5$ mg/L, homocysteine $<9-10$ micromoles/L (microvascular defense), STOP-BANG OSA screen. | Xie & Nedergaard 2013 ([PMID: 24136966](https://pubmed.ncbi.nlm.nih.gov/24136966)), Cotman 2002 ([PMID: 12052608](https://pubmed.ncbi.nlm.nih.gov/12052608)), Smith 2016 ([PMID: 26644383](https://pubmed.ncbi.nlm.nih.gov/26644383)) |
| [`USER_centenarian_athletic_reserve.md`](./scaffolds/USER_centenarian_athletic_reserve.md) | Centenarian Decathlon, functional reserve surplus, loaded carries, grip bar hangs. | Joint integrity over 1RM, multi-planar lateral/rotational stability, trip-recovery reflexes. | Harridge & Lazarus 2017 ([PMID: 28028824](https://pubmed.ncbi.nlm.nih.gov/28028824)), Mandsager 2018 ([PMID: 30646198](https://pubmed.ncbi.nlm.nih.gov/30646198)), Reid 2012 ([PMID: 22766023](https://pubmed.ncbi.nlm.nih.gov/22766023)) |
| [`USER_cycling_female.md`](./scaffolds/USER_cycling_female.md) | Individualized symptom autoregulation over dogmatic cycle-syncing, luteal protein/hydration adjustments. | Serum ferritin deficiency triage (same-lab rule), exercise hepcidin kinetics, IOC REDs CAT2 continuum. | Mountjoy 2023 ([PMID: 37752011](https://pubmed.ncbi.nlm.nih.gov/37752011)), Elliott-Sale 2021 ([PMID: 33606213](https://pubmed.ncbi.nlm.nih.gov/33606213)), Stoffel 2017 ([PMID: 29032957](https://pubmed.ncbi.nlm.nih.gov/29032957)) |
| [`USER_perimenopause_longevity.md`](./scaffolds/USER_perimenopause_longevity.md) | Supervised HiRIT osteogenic loading (LIFTMOR), visceral fat clearance, non-hormonal VMS neuromodulation. | STRAW+10 clinical diagnosis, MHT contraindications screen, intact uterus progestogen rule, ISCD Z/T-scores. | Harlow 2012 ([PMID: 22378897](https://pubmed.ncbi.nlm.nih.gov/22378897)), NAMS 2022 ([PMID: 35797481](https://pubmed.ncbi.nlm.nih.gov/35797481)), Watson 2018 ([PMID: 28975661](https://pubmed.ncbi.nlm.nih.gov/28975661)) |
| [`USER_cardiometabolic_male.md`](./scaffolds/USER_cardiometabolic_male.md) | Elite cardiorespiratory fitness, Zone 2 mitochondrial lactate oxidation, visceral fat reduction. | Lifetime cumulative ApoB targets ($<80/<65$ mg/dL), Lp(a), CAC/CTCA triage, FIB-4, TRT hematocrit/PSA screen. | Mach ESC/EAS 2020 ([PMID: 31473770](https://pubmed.ncbi.nlm.nih.gov/31473770)), Ference 2018 ([PMID: 28448937](https://pubmed.ncbi.nlm.nih.gov/28448937)), Bhasin 2018 ([PMID: 29562364](https://pubmed.ncbi.nlm.nih.gov/29562364)) |
| [`USER_concurrent_athlete.md`](./scaffolds/USER_concurrent_athlete.md) | Temporal separation of AMPK vs mTORC1, leucine threshold, collagen and vitamin C pre-loading. | Bidirectional SWC autonomic recovery gating (sympathetic exhaustion vs parasympathetic saturation), tendon repair. | Baar 2014 ([PMID: 24728927](https://pubmed.ncbi.nlm.nih.gov/24728927)), Coffey & Hawley 2017 ([PMID: 27396360](https://pubmed.ncbi.nlm.nih.gov/27396360)), Plews 2013 ([PMID: 23852723](https://pubmed.ncbi.nlm.nih.gov/23852723)) |
| [`USER_elder_sarcopenia.md`](./scaffolds/USER_elder_sarcopenia.md) | High-Velocity Resistance Training (HVRT Type II motor units), protein floor, creatine, dynamic balance. | SARC-F case finding, EWGSOP2 ASMM cutoffs, baseline eGFR renal gate before protein escalation, Beers audit. | Cruz-Jentoft 2019 ([PMID: 30312372](https://pubmed.ncbi.nlm.nih.gov/30312372)), Bauer 2013 ([PMID: 23867520](https://pubmed.ncbi.nlm.nih.gov/23867520)), Fielding 2014 ([PMID: 24866862](https://pubmed.ncbi.nlm.nih.gov/24866862)) |
| [`USER_metabolic_reset_glp1.md`](./scaffolds/USER_metabolic_reset_glp1.md) | Sarcopenia defense (compound resistance training), CGM glycemic targets, non-negotiable step floor. | Black Box contraindications (MTC, MEN 2, pancreatitis), baseline eGFR, gradual soluble fiber titration, AKI fluid floor. | Wilding 2021 ([PMID: 33567185](https://pubmed.ncbi.nlm.nih.gov/33567185)), Prado 2024 ([PMID: 38552634](https://pubmed.ncbi.nlm.nih.gov/38552634)), Battelino 2019 ([PMID: 31177185](https://pubmed.ncbi.nlm.nih.gov/31177185)) |
| [`USER_pregnancy_postpartum.md`](./scaffolds/USER_pregnancy_postpartum.md) | Linea alba fascial tension restoration, return-to-impact 4-part strength battery, lactational energy surplus. | ACOG 804 maternal red flags (vaginal bleeding, contractions, DVT signs), thermal cap, BSI surveillance. | ACOG 804 2020 ([PMID: 32217980](https://pubmed.ncbi.nlm.nih.gov/32217980)), Mottola 2018 ([PMID: 30337460](https://pubmed.ncbi.nlm.nih.gov/30337460)), Goom 2019 |

---

## Persona $\longleftrightarrow$ Scaffold Cross-Mapping Matrix

Highlander's two tiers are fully orthogonal. Any persona can be paired with any physiological scaffold:

| Psychological Persona (`SOUL.md`) | Exemplar Physiological Scaffold (`USER.md`) | Combined Archetype Synergy |
|---|---|---|
| **Operator** | `USER_concurrent_athlete.md` | High-agency hybrid athlete tracking molecular signaling (AMPK/mTORC1) with zero tolerance for stalled loops. |
| **Scholar** | `USER_cardiometabolic_male.md` | Data-driven biohacker tracking lifetime cumulative ApoB, CTCA soft plaque, and Mendelian randomization hazard ratios. |
| **Catalyst** | `USER_centenarian_athletic_reserve.md` | High-enthusiasm builder attacking the Centenarian Decathlon benchmarks and building multi-decade functional surplus. |
| **Visionary** | `USER_mitochondrial_vitality.md` | Strategic longevity architect optimizing cellular bioenergetics, PGC-1alpha induction, and metabolic flexibility. |
| **Guide** | `USER_perimenopause_longevity.md` | Consultative concierge navigating STRAW+10 staging, MHT contraindications, and LIFTMOR osteogenic loading. |
| **Concise** | `USER_cognitive_neurolongevity.md` | Time-starved executive receiving crisp 2-bullet daily interventions for BDNF induction, daylight timing, and sleep wash. |
| **Rebuilder** | `USER_metabolic_reset_glp1.md` | Guilt-free habit restorer protecting lean muscle mass, protein floors, and step consistency during GLP-1 therapy. |
| **Protector** | `USER_cycling_female.md` | Decompressor buffering against RED-S, menstrual cycle tracking anxiety, and overtraining with autoregulated deloads. |

---

## The Three Files

| File | Holds | Changes |
|---|---|---|
| `SOUL.md` | Identity, stance, communication rules, and the coaching loop | Rarely |
| `USER.md` | Durable facts about the person (biology, goals, baseline, preferences) | Occasionally |
| `MEMORY.md` | Working state and active feedback loops (pays rent every turn) | Constantly |

`SOUL.md` is who the agent is. `USER.md` is who the person is. `MEMORY.md` is what is true right
now. Skills are the *verbs* the loops call.

## The Coaching Loop

Every `SOUL.md` here carries the canonical loop block:

> **Ingest → Verify → Interpret → Decide → Plan → Deliver proactively → Learn**

1. **Ingest** — read wearable and activity streams on a schedule without being prompted.
2. **Verify** — verify raw numbers before interpreting them. Disagreements between sensors are surfaced,
   not smoothed over.
3. **Interpret** — evaluate against personal baselines and longitudinal context, not generic population averages.
4. **Decide** — keep interventions proportional; most questions need an immediate, actionable answer.
5. **Plan** — structure habits and training sessions into weekly calendar anchors.
6. **Deliver proactively** — at most **one** proactive message a week, scheduled to quiet-hours preferences.
   If there is nothing meaningful to say, say nothing.
7. **Learn** — observe adherence, record outcomes, adapt to feedback, and audit memory context rent.

## Instantiating a Template

[ONBOARDING.md](../ONBOARDING.md) Step 7 walks through the interactive persona interview and setup.
The three files only take effect where Hermes expects them:
- `SOUL.md` → `~/.hermes/SOUL.md` (or `~/.hermes/profiles/<name>/SOUL.md`)
- `USER.md` → `~/.hermes/memories/USER.md` (or `~/.hermes/profiles/<name>/memories/USER.md`)
- `MEMORY.md` → `~/.hermes/memories/MEMORY.md` (or `~/.hermes/profiles/<name>/memories/MEMORY.md`)

No gateway restart is needed for profile files — they are read fresh on every turn.

## Scaffolds, Not Redactions

The content here was written from the ground up to be generic templates. There is no original personal
data hiding underneath, and no identifiers are carried over. Use placeholders (`<USER>`, `<AGE>`, `<CITY>`,
`<ROLE>`, `<LANGUAGE>`, `<MODALITIES>`, `<INJURIES>`, `<INTOLERANCES>`, `<MEDICATIONS>`, `<DEVICE>`,
`<CADENCE>`) when adapting templates for personal deployment.
