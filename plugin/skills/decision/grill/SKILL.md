---
name: grill
license: MIT
description: "Use when facing 'should I do/build/adopt X?' — a real decision with stakes. Null hypothesis = NO, adversary must prove YES. Adversarial analysis via native Hermes subagents. For binary decisions, not exploration."
version: 1.2.0
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [decision, adversarial, grill, subagent, delegate_task]
---

# Grill — Adversarial Decision Analysis (Native Subagents)

Stress-test proposals through adversarial research. **Default answer is NO — research must prove YES.**

Use for high-stakes or hard-to-reverse decisions (money, time, architecture). For small calls use your own judgment or **peer-review**.

> **Privacy / data handling:** Prompts and any context you include are sent to the **active model provider** for subagents. **Keep sensitive health data and personal identifiers out of prompts unless the user explicitly agrees** to include them.

## Scope

| Scope | Flag | Agents | When |
|-------|------|--------|------|
| **Standard** | *(default)* | Adversary + Builder + Pragmatist | Multi-file or multi-claim decisions |
| **Light** | `--light` | Adversary only | Quick kill-test on a single claim |
| **Deep** | `--deep` | + External Researcher | External tools/frameworks involved |

## Process

### Step 1: Frame

Read the proposal. Extract: **decision question** (one sentence), **null hypothesis** (NO), **kill condition**, **fact claims**, **external claims**. Challenge the framing, **steelman** the proposal, and state the kill condition up front.

### Step 2: Probe (native subagents)

Fire agents via `delegate_task` (Adversary first; Builder/Pragmatist/External Researcher in parallel when independent). **No-interrupt warning:** active children can be cancelled if interrupted.

**Context checklist for every subagent** (fresh context): proposal text/path, project root and relevant file paths, test command if applicable, out-of-scope notes, required headings `## Findings`, `## Simpler Alternative`, `## Confidence`. Remind: keep sensitive/health data out unless the user agreed.

Suggested `toolsets`: Adversary/Builder/Pragmatist `["file", "terminal"]` (or `["file"]` if sufficient); External Researcher (deep) `["web"]`.

#### Adversary (always)
Verify claims against codebase, then argue against adoption. For each idea give the simplest alternative and % value retained, the 3 strongest reasons to reject, underplayed risks/contradictions, and cost of undoing (LOW/MEDIUM/HIGH). Cite specifics (paths/lines). Run the Adversary as a `delegate_task` subagent.

#### Builder (standard/deep)
Feasibility: trace code paths, realistic effort (optimistic × 1.5–2.0), hidden dependencies, reusable patterns, 80% version.

#### Pragmatist (standard/deep)
Actual problem solved, worth/cost (time, infra, maintenance, opportunity cost), “would you fund it?”

#### External Researcher (deep only)
Verify external claims (features, maintenance, issues/breaking changes) with sources. If unreachable, mark claims **Unverified** and report what was attempted.

### Step 3: Synthesize

Main agent only. **Quality gate** (evidence/substance), **kill condition check** (stop if met), **contradictions & simplicity audit**, then verdicts:

| Verdict | Means |
|---------|-------|
| **GO** | Verified valuable, no simpler alternative, feasible, no fatal risks |
| **CONDITIONAL-GO** | Valuable but needs conditions met (list them) |
| **DOWNGRADE** | Simpler alternative retains ≥70% value |
| **NO-GO** | Debunked facts, fatal risks, or not worth it |
| **DEFER** | Insufficient info — needs user input or more research |

### Step 4: Present

```md
## Grill: {Title}
**Decision**: {GO / CONDITIONAL-GO / DOWNGRADE / NO-GO / DEFER}

### Per-Idea Verdict
| Idea | Verdict | Simpler Alternative | Key Risk |

### Fact Corrections
{what was wrong}

### External Verification
{confirmed or debunked}

### Unverified Claims
{treat as assumptions}
```

## Pitfalls

- Don’t ask “How can X help?” — ask “Should we use X?” (null = NO). Don’t skip Adversary (or External Researcher for external tools).
- Don’t trust consensus — weight by evidence. Separate facts from assumptions. Prefer simpler alternatives.
- **Privacy:** don’t paste health/personal data into prompts unless the user agreed.
- **Verify negative file claims** yourself before accepting (“not found/can’t verify” can be a context limitation). 

## Notes

Keep subagent prompts focused and include only the context needed for the decision (see privacy note above).
