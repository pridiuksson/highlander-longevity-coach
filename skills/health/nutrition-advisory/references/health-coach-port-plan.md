# Health Coach — Port Plan & Architecture Reference

> Source: highlander-longevity-coach/.claude/skills/health-coach/ (Claude Code skill)
> Status: Evaluated through run-004, not yet ported to Hermes
> Integration: This is Layer 3 in the nutrition-advisory architecture

## What Exists (highlander-longevity-coach repo)

A fully-built and evaluated multi-expert health debate skill with:
- **4 domain experts**: Longevity Scientist, Dietitian, Sports Medicine, Pragmatist
- **1 validator**: fact-checks claims per round with [OK]/[WARN]/[FAIL] tags
- **5-phase debate**: independent analysis → structured critique → sequential discussion → final positions → synthesis
- **JSON artifacts**: each run produces `debate.json` with all phases (state machine)
- **Eval harness**: separate `eval-health` skill, golden questions, coverage/hallucination/debate-quality metrics

Location: `~/highlander-longevity-coach/.claude/skills/health-coach/`

| File | Purpose |
|------|---------|
| `SKILL.md` | 5-phase orchestration instructions (374 lines) |
| `REFERENCE.md` | Prompt templates for all phases |
| `personas/longevity-scientist.md` | Biomarkers, aging, longevity interventions |
| `personas/dietitian.md` | Nutrition, supplements, metabolic health |
| `personas/sports-medicine.md` | Exercise, recovery, sleep, training load |
| `personas/pragmatist.md` | Actionable habits, constraints, adherence |
| `personas/validator.md` | Fact-checking protocol |

## Eval History

| Run | Experts | Turns | WARN | FAIL | Quality | Key Finding |
|-----|---------|-------|------|------|---------|-------------|
| run-001 | 2 | 2 | 0 | 0 | PASS | Must-mention 100%, disagreements surfaced |
| run-003 | 4 | 4 (bug) | 15 | 1 | — | CYP errors, creatine-rhabdo myth, fabricated causal narrative |
| run-004 | 4 | 8 | 7 | 0 | FAIL (strict) | 70% WARN reduction, 0 FAIL, all precision issues not safety |

Run-004 improvement plan in `~/highlander-longevity-coach/Knowledge/Plans/evals-run-003.md` — 3 phases of fixes, Phase 1 completed (guardrails + evidence updates + serialization).

## Domain Expert Profiles (Summary)

| Expert | Focus | Adversarial Angle | Key Strength |
|--------|-------|-------------------|-------------|
| Longevity Scientist | Biomarker interpretation, optimal vs reference ranges, aging trajectories | Challenges anything not backed by longitudinal studies | Evidence quality tags ([STRONG]/[MODERATE]/[WEAK]) |
| Dietitian | Supplement stack audit, nutrient interactions, dietary patterns | Challenges supplement stacks — most unnecessary with proper diet | Full interaction matrix, CYP enzyme claims |
| Sports Medicine | Exercise programming, recovery, sleep architecture | Challenges overtraining — more is not always better | Sleep analysis, training load monitoring, ferritin trajectory |
| Pragmatist | Actionable habits, cost-benefit, adherence | Challenges complexity — if hard to maintain, it won't work | Effort-impact matrix, minimum viable protocol |

## Port to Hermes — Key Changes

### Orchestration: spawn_agent → delegate_task

The Claude Code version uses `spawn_agent` (internal sub-agent spawning). Hermes equivalent is `delegate_task`. Key differences:
- `delegate_task` subagents inherit the parent model (no per-call model selection)
- Subagents have NO memory of parent conversation — all context must be passed explicitly via `context` field
- Leaf subagents cannot use `clarify`, `memory`, `send_message`, `execute_code`
- Nested delegation is OFF (max_spawn_depth=1) — all children are leaves

### Two Orchestration Modes

**Mode 1: Full Debate** (for contested decisions)
- Port the 5-phase structure directly
- Phase 1/2/4: parallel `delegate_task` calls (batch mode, up to 5 tasks)
- Phase 3: sequential `delegate_task` calls (each turn depends on prior)
- Phase 5: single `delegate_task` call
- Each subagent receives: persona prompt + health data (<YOUR_BASELINE_DOC>.md) + prior phase JSONs
- JSON state machine: same `debate.json` file pattern

**Mode 2: Synthesis Pipeline** (for prioritization/system-building tasks)
- Stage A: 4 parallel `delegate_task` calls (experts return ~200 word briefs)
- Stage B: 1 `delegate_task` call (synthesizer gets briefs + health data + question)
- Optional: run validator on final output via CLI (command-code or agy)
- Much faster (~2 min vs ~8 min), more coherent single-voice output

### Persona Files — Can Be Reused As-Is

The persona markdown files from highlander-longevity-coach are platform-agnostic. They describe roles, not orchestration. Copy directly to `$HERMES_HOME/skills/nutrition-advisory/personas/` (or wherever the Hermes health-coach skill lands).

### Health Data — <YOUR_BASELINE_DOC>.md Is the Shared Context

Both modes pass `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md` (or `<YOUR_HEALTH_DIR>/health-profile.md`) to every subagent. The file is ~600 lines — fits in every context window. No database needed.

## Decision: When to Build

Build Layer 3 when:
- A health question requires genuine multi-domain expertise (not just nutrition research filter)
- The question involves contested trade-offs (debate mode) OR complex synthesis across 600+ lines of data (synthesis mode)
- Single-agent analysis produces conflicting priorities that need domain-expert resolution

Don't build preemptively. Let real questions drive the build. The first candidate: "draft a life operating system" — the synthesis pipeline pattern.

## Related Files in highlander-longevity-coach

| File | Content |
|------|---------|
| `Knowledge/Plans/health-coach.md` | Original project brief (421 lines) |
| `Knowledge/Plans/health-coach-implementation.md` | Implementation status, remaining work |
| `Knowledge/Plans/health-skill-architecture.md` | Three-layer architecture history |
| `Knowledge/Plans/evals-run-003.md` | Improvement plan, Phase 1-3 |
| `Knowledge/Research/Tech/multi-agent-debate-frameworks.md` | Quorum, swarm-debate, agent-for-debate comparison |
| `<YOUR_HEALTH_DIR>/evals/run-004/eval-report.md` | Latest eval report (199 lines) |
| `<YOUR_HEALTH_DIR>/evals/run-004/debate.json` | Latest debate transcript |

## Key Anti-Patterns (from eval history)

1. **Confident interpolation** — experts present associated concepts as facts (CYP enzyme claims, optimal ranges as guidelines). Fix: per-persona guardrails.
2. **Fabricated causal narratives** — experts construct plausible causal chains without evidence ("sleep variability explains supplement stacking"). Fix: Pragmatist guardrail requiring "hypothesis" label.
3. **Creatine-rhabdo conflation** — persistent myth from CK naming confusion. Fix: explicit Sports Medicine guardrail.
4. **Validator findings ignored** — experts didn't engage with [WARN] corrections in subsequent turns (0-14% acknowledgment rate). Fix: structural Evidence Updates injection (implemented in run-004, not yet re-evaluated).
5. **Inventory ≠ intake** — building analyses on products the user doesn't actually take. Fix: mandatory Step 2d in nutrition-advisory.
