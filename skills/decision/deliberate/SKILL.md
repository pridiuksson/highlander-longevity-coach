---
name: deliberate
license: MIT
description: "Use for complex questions spanning MULTIPLE domains with genuine tension between perspectives (e.g. health + behavior + training). 5-phase expert debate with model-independent validation (~5min). NOT for quick checks (peer-review) or binary decisions (grill)."
version: 1.0.0
trigger: "Multiple domains pull in different directions and a single opinion won't resolve the tension."
tags: [deliberation, debate, multi-expert, health, synthesis]
---

# Deliberate — Multi-Expert Deliberation

Spawn domain experts. Let them disagree. Validate independently. Synthesize into one coherent answer. **You are the judge, not a dumb router.**

## When to Use

```
Is this a quick sanity check?
└─ YES → Use peer-review (Tier 1)

Is this a binary decision ("should I do X?")?
└─ YES → Use grill (Tier 2, null hypothesis = NO)

Does this span multiple domains with genuine tension?
└─ YES → Deliberate (Tier 3)
```

**Tier 3 triggers:**
- Question requires reconciling conflicting expert perspectives
- Multiple domains pull in different directions (e.g., nutrition vs training vs sleep)
- Output should feel like ONE coherent philosophy, not a treaty
- The question is exploratory, not binary

**NOT for:**
- Quick opinions → peer-review
- "Should I adopt X?" → grill
- Single-domain questions → just answer it directly

## Self-Encapsulation

This skill owns everything it uses. No cross-skill imports. No shared scripts with peer-review or grill. If those skills evolve, this skill is unaffected. Harmony through patterns, not shared code.

## Overview

```
Hermes frames the question and selects domain pack
  ↓
Phase 1: 4 experts in parallel (delegate_task) → structured briefs
  ↓
Phase 2: 4 experts critique each other (delegate_task) → AGREEMENTS/DISAGREEMENTS/MISSING
  ↓
Phase 3: 8 sequential turns + validator after each (delegate_task + CLI) → discussion + fact-checks
  ↓
Phase 4: 4 experts state final position (delegate_task) → position + confidence
  ↓
Phase 5: Synthesizer via CLI (model-independent) → verdict + key insight + the answer
  ↓
Hermes judges the output (orchestrator-as-judge)
```

## Setup

### Step 1: Frame the Question

Before spawning any agent, answer these:

1. **Decision question**: one sentence. What are we trying to answer?
2. **Domain pack**: which `domains/<name>/` directory? (e.g., `health/`)
3. **Data**: what file(s) do experts need? (e.g., `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`). For training/recovery/sleep questions ALSO generate a wearable-data brief from `$HERMES_HOME/data/health.db` (see `samsung-health-import` skill — schema + verified mappings): 4-week workout load by type, 2-week nightly RMSSD + RHR, sleep duration trend, latest body comp, and the data end-date. Experts get real series, not recollections. Tier rules apply: anchor on RMSSD/RHR/sleep-duration/workout-minutes; VO2max (watch estimate) is LOW-CONFIDENCE (contradicts RMSSD+RHR trends — suspect device re-estimation); stage splits are trend-indicative only.
4. **Quality criteria**: how will I judge the output? (coverage, disagreement, actionability)

### Step 2: Create Run Directory

```bash
# Find the next run number
ls $HERMES_HOME/skills/deliberate/runs/ 2>/dev/null | grep 'run-' | sort -V | tail -1
# Create next
mkdir -p $HERMES_HOME/skills/deliberate/runs/run-NNN
```

Initialize `debate.json`:

```json
{
  "run": "run-NNN",
  "question": "<your question>",
  "domain": "health",
  "created_at": "<ISO timestamp>",
  "phases": {}
}
```

### Step 3: Load Personas

Read all persona files from `domains/<name>/`. Each persona prompt gets injected into the corresponding expert's `delegate_task` call.

### Step 4: Load Data

Read the data file(s) (e.g., `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`). Every expert receives the full data.

## Parent probes + corrections ledger (validated runs 006/007, 2026-08-29)

Before Phase 1: run cheap deterministic checks yourself on any contested number in the brief (sensitivity analyses, confound controls, era/matched-window strata, multiplicity families) and write results into the brief as PARENT PROBES. Experts deliberate judgment over measurable facts — never let them guess something a 10-second probe answers. Validated examples: HRmax sensitivity (`est = a + b×HRmax` ⇒ ±<YOUR_RESTING_HR_BPM> = ±0.55 → "inert"); cohab-era stratum exposing a run-tail as era-confounded; duration-band control collapsing a "floor" effect.

When evidence lands MID-deliberation: append it to a numbered CORRECTIONS LEDGER in the brief + `debate.json` (`phases.pre_delib_corrections`), and inject into every later phase with explicit wording that it OVERRIDES stale claims. All five run-006 corrections were conservative downgrades and every one propagated to visible expert retractions.

**Phase-2 replacement (run-007)**: when the question is convergent rather than conflictual, instruct every expert to produce an independent `## Verdict Audit` tiering the SAME 4-5 key numbers ([corroborated]/[weak]/[contested]). Four-way independent tiering IS the cross-examination; record the deviation rationale in `phases.phase2`. Remaining normative disagreements (e.g. formalize-training vs change-nothing) are resolved by PRE-REGISTERED DECIDING RULES ("if TT-VDOT <45 or a race goal appears ⇒ formalize; else change nothing"), not by panel vote.

**Gate before dispatch (added 2026-08-30 after run-008's partial voiding):** the panel can only be as good as the series it votes on. Before ANY deliberation dispatch, the parent must (a) list every load-bearing input series (the ones hypotheses stand or fall on), (b) re-derive each from raw data with an independent method, and (c) anchor-check against human testimony ("does this match lived experience?"). Run-008 voted 4-0 on a nap-contaminated bedtime series and a non-reproducible unscored-gap series; one sentence of user testimony ("bedtime has been 23:20-23:40 for a year") falsified both. Testimony beats a buggy probe; a probe that reproduces beats testimony.

**Predictive-question extension (added after run-009 gate-block, 2026-09-11):** when the question asks to PREDICT a numeric outcome ("predict risk X", "what will metric Y be"), the gate requires a 4-part predictive-input checklist: (1) the predictive framework (e.g. risk calculator, epidemiology-only); (2) all predictive-series inputs the framework needs; (3) confirmation of each in raw data (independent grep/file-read); (4) explicit user testimony confirming or denying absence-of-tracking inputs (family history, infection status, exposure history). If ANY predictive-series input is MISSING: do NOT spawn experts — spawning 4 experts to invent a number is the run-008 failure mode. Halt at Phase 0; document missing inputs; ask the user; produce a parent-derived synthesis with zero fabricated numbers. Full protocol + verified gastric-cancer example (4 predictive inputs MISSING; only exposure = smoked salmon ≤5x/wk, IARC Group 3, no threshold model; profile LOW-not-quantifiable): see `references/predictive-input-gate.md`.

## Phase 1: Independent Analysis

**Goal**: 4 independent perspectives, no cross-referencing.

Spawn 4 experts **in parallel** via `delegate_task`. Each expert gets:
- Their persona prompt (from `domains/<name>/<expert>.md`)
- The full data file content
- The question
- Output format instructions (see template below)

**Output format per expert** (use `templates/brief.md` as the structure):
```markdown
## Top 3 Constraints
(List the 3 most important constraints this data reveals for the question)

## Top 3 Priorities
(The 3 things that matter most, ranked)

## Biggest Risk
(Where does the biggest danger lie that others might miss?)

## Confidence
HIGH / MEDIUM / LOW — with one-sentence justification
```

After all 4 complete, append to `debate.json`:
```json
{
  "phases": {
    "phase1": {
      "name": "independent_analysis",
      "responses": {
        "<persona_name>": "<full response text>",
        ...
      }
    }
  }
}
```

Write `debate.json` back to disk.

## Phase 2: Structured Critique

**Goal**: Surface genuine disagreements between experts.

Spawn 4 experts **in parallel** via `delegate_task`. Each gets:
- Their persona prompt
- Data
- Question
- ALL Phase 1 responses (from `debate.json`)
- Instruction: produce a structured critique

**Output format per expert:**
```markdown
## AGREEMENTS
(Points where you agree with other experts)

## DISAGREEMENTS
(Points where you disagree — name the expert and the specific claim)

## MISSING
(What no other expert mentioned that they should have)
```

Append to `debate.json` as `phase2`.

### Phase-2 replacement: Verdict Audit (validated run-007)
When the question is convergent rather than conflictual, instruct every expert to produce an independent `## Verdict Audit` tiering the SAME 4-5 key numbers ([corroborated]/[weak]/[contested]). Four-way independent tiering IS the cross-examination; record the deviation rationale in `phases.phase2`. Resolve remaining NORMATIVE disagreements with PRE-REGISTERED DECIDING RULES in the brief ("if <metric> <threshold> or <goal> ⇒ <action>; else do nothing"), not panel votes — run-007's hill-slot-vs-nothing deadlock merged into one operational rule this way.

### Attribution questions: discriminator tables + % allocations (run-008 pattern)
For "which cause explains X" debates, build the brief around a discriminator table: rival hypotheses as columns, observable signatures as rows, each cell marked SUPPORTS/WEAK/CONTRADICTS. Then require every expert to allocate % confidence across hypotheses, not pick a winner. Compute the table's rows yourself from data first — the strongest discriminators are accounting identities (e.g. staged-time total vs measured duration exposing "unscored time"; flat REM share + flat efficiency + vanished deep minutes = selective deletion, not redistribution).

## Phase 3: Discussion + Validator

**Goal**: Sequential debate with model-independent fact-checking after each turn.

**Turn count**: Minimum 8 (2 rounds × 4 experts). Do NOT exit early.

**Judge compression escape-hatch (validated run-006, 2026-08-29)**: the 8-turn
sequential format is the default, not a hard requirement. If (a) Phase 2
critiques already cross-examined every brief by name, AND (b) new evidence
landed mid-deliberation that changes what the remaining turns would argue
about (e.g. a parent correction invalidating a contested claim), the judge MAY
compress Phase 3 to a single parallel final-position round — each expert sees
all briefs + critiques + the new evidence, rebuts, commits — with validator
checks per position, feeding the normal Phase 5 synthesis. Record the
deviation in `debate.json` (`phases.phase3.deviation_rationale`). Substance
that must survive compression: cross-examination actually happened (Phase 2
did it), mid-flight evidence reached every expert with an explicit OVERRIDE
instruction, the validator stays CLI/model-independent. Do NOT compress merely
to save spawns when Phase 2 was thin or the question is genuinely multi-round.

**Turn order**:
Round 1: expert1 → expert2 → expert3 → expert4
Round 2: expert1 → expert2 → expert3 → expert4

**Per turn:**

1. Read `debate.json` to get full history
2. Spawn the speaking expert via `delegate_task` with:
   - Their persona prompt
   - Data
   - Question
   - All Phase 1 responses
   - All Phase 2 critiques
   - Discussion history so far (from `debate.json.phases.phase3.turns`)
   - Evidence updates from previous validator findings
   - Turn number and guidance
3. Expert makes ONE focused point (≤300 words)
4. **Run the validator** via CLI:
   ```bash
   $HERMES_HOME/skills/deliberate/scripts/deliberate-validator.sh "<validator_prompt>"
   ```
   Where `<validator_prompt>` is constructed from:
   - Validator persona (from `domains/<name>/validator.md`)
   - The expert's response text
   - Instruction to tag claims as [OK], [WARN], [FAIL]
5. Parse validator output for tagged findings
6. Append the turn to `debate.json.phases.phase3.turns`
7. Extract validator findings as "Evidence Updates" for the next turn

**Evidence updates format** (injected into next expert's prompt):
```
## Evidence Updates
⚠️ (Expert Name, Turn N): <claim> — Validator notes: <finding>
✅ (Expert Name, Turn N): <claim> — Verified
```

**Turn guidance:**
| Turn | Guidance |
|------|----------|
| 1 | Opening: set the direction |
| 2-3 | Focus on key disagreements |
| 4-6 | Build toward synthesis and common ground |
| 7 | Start wrapping up key points |
| 8 | FINAL TURN: make it count |

## Phase 4: Final Positions

**Goal**: Each expert states their evolved position.

Spawn 4 experts **in parallel** via `delegate_task`. Each gets:
- Their persona prompt
- Data
- Question
- Complete Phase 3 discussion history
- Validator findings summary

**Output format:**
```markdown
## Position
(Your final position, 3-5 sentences)

## What Changed
(How your position evolved from Phase 1, or why it didn't)

## Confidence
HIGH / MEDIUM / LOW
```

## Phase 5: Synthesis

**Goal**: Model-independent synthesis into one coherent answer.

Run via **CLI** (not delegate_task) for model independence:

```bash
$HERMES_HOME/skills/deliberate/scripts/deliberate-validator.sh "<synthesis_prompt>"
```

The synthesis prompt includes:
- Data
- Question
- All Phase 4 final positions
- Validator findings summary
- Instruction to produce:

```markdown
## Bottom Line
(1-2 sentences — the answer)

## Key Insight
(One quotable insight from the debate)

## The Answer
(Structured guidance — concrete, actionable, specific)

## Safety Considerations
(Who should consult a doctor before acting on this)

## Caveats
(Individual variation notes, evidence gaps)

## Consensus
FULL / PARTIAL / NONE

## Notable Disagreements
(What the experts couldn't agree on)
```

Append to `debate.json` as `phase5`.

## Judging Protocol (Orchestrator-as-Judge)

After Phase 5, Hermes evaluates the output. NOT a dumb router — use your own judgment.

**Critical: Document verification AFTER deliberation.** Deliberation output will be written into reference documents (<YOUR_TRAINING_PLAN>.md, <YOUR_NUTRITION_PLAN>.md, etc.). These documents will be read by future sessions and treated as ground truth. **Any factual error in the synthesis that propagates into a document becomes invisible — it's surrounded by correct information and looks authoritative.** This is how the iron threshold error (run-003 food strategy deliberation was cited as the source for iron decisions that actually came from run-002) went undetected for days. After writing deliberation output to persistent documents, run an independent peer-review on EACH document separately, supplying the reviewer with key facts NOT in the document being reviewed. This catches cross-document contradictions and factual errors that a single-pass synthesis misses.

**Check these (in order):**

1. **Did experts actually disagree?** If all 4 agreed on everything, the domain pack is weak or the question didn't have real tension. The debate added nothing over a single opinion.

2. **Did the validator catch real errors?** If 0 flags across 8 turns, the validator is under-sensitive. If >10 flags, the experts are unreliable. Target: 3-10 flags.

3. **Does the synthesis survive contact with the data?** Read the synthesis. Does it contradict anything you know about the data that the experts missed? If Hermes can identify a contradiction, flag it.
3.5 **Trace every number in the synthesis to primary data** (run-006: 15/15 traced to the DB, 0 contradictions). A number you cannot trace — especially placement claims like percentiles asserted without a source table — gets flagged as expert judgment in the debate record or removed from the delivered summary.

4. **Is the output better than what you could produce alone?** The substance check. Could Hermes have written the synthesis from the data alone? If yes, the multi-agent structure added no value.

5. **Are the recommendations actionable?** "Consult your doctor" is not actionable. "Add beets to your buffet lunch 3x/week for betaine" is.

**Present to user:**
- The synthesis (from Phase 5)
- Debate quality: consensus level, disagreement count, validator findings
- Your judgment: did this debate add value over a single opinion?
- Full transcript: `$HERMES_HOME/skills/deliberate/runs/run-NNN/debate.json`

## Iterating on Personas

To improve deliberate's output quality over time:

1. Run deliberate (Phases 1-5) → produce synthesis
2. Eval the run: coverage, hallucination rate, disagreement density, actionability
3. Quality insufficient? Adjust persona prompts (guardrails, adversarial stances, templates)
4. Re-run deliberate → re-eval → compare to prior run
5. Repeat until eval metrics stabilize across multiple question types

State lives in eval reports. No separate state file needed — the eval reports ARE the state.

## Domain Packs

Each domain is a directory under `domains/` with persona files:

```
domains/
└── health/
    ├── longevity-scientist.md
    ├── dietitian.md
    ├── sports-medicine.md
    ├── pragmatist.md
    └── validator.md
```

**Adding a new domain:** Create `domains/<name>/` with persona files. Each persona should be 80-120 lines with:
- Domain focus section
- Adversarial stance (what this expert challenges)
- Confidence calibration table
- Per-persona failure-mode guardrails (if known)

## Constraints

- **Self-encapsulated.** No cross-skill imports. Own scripts, own personas, own templates.
- **Sequential phases.** Phase N must complete before Phase N+1 starts.
- **Parallel within phases.** Phases 1, 2, and 4 spawn experts simultaneously. Phase 3 is sequential.
- **8 turns minimum in Phase 3.** No early termination regardless of apparent consensus.
- **Health data in every prompt.** Every expert receives the full data file.
- **Orchestrator judges.** You do NOT blindly present expert output. You evaluate quality.
- **Synthesizer via CLI.** Phase 5 runs through an external CLI for model independence.
- **Validator via CLI.** Phase 3 validator runs through an external CLI for model independence.

