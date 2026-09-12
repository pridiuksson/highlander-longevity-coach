# Async RL Iteration Patterns

Condensed findings from researching GLM-5/slime/SkyRL (Jun 2026) for iteration loop improvements. Only patterns that survived peer-review as genuinely transferable to text-based agent loops are included.

## Sources

- **THUDM/slime** (github.com/THUDM/slime) — the async RL engine behind GLM-5. Cloned and source-read.
- **NovaSky-AI/SkyRL** (github.com/NovaSky-AI/SkyRL) — Berkeley's modular RL library for LLM agents.
- **GLM-5 paper** (arXiv 2602.15763) — technical report covering async agent RL algorithms.

## Pattern 1: Clean Eval (from slime coding_agent_rl)

slime's `examples/coding_agent_rl/generate.py` runs a 4-stage orchestrator: prepare_workspace → harness.run → git_diff → **evaluate in fresh sandbox**. The agent works in sandbox A; evaluation happens in a *pristine sandbox B* with only the diff applied. The agent cannot have corrupted the evaluation environment.

**Transfer to loop skill:** Before the checker verifies, detect if the maker modified verification criteria. `git diff HEAD -- <test files>` distinguishes "maker changed existing tests" (reject) from "maker added new tests" (allow).

## Pattern 2: Diagnostic Capture at Failure Boundaries

slime's `_log_timeout_diagnostic()` dumps pending asyncio task names when the wall-clock guard fires. SkyRL's generators have per-trajectory retries, context-length filtering, and agent-timeout loss-masking.

**Transfer to loop skill:** On timeout, capture `git diff --name-only`, last tool calls, and running processes *before* recording the failure. Append diagnostics to the retry context so the next attempt knows what was partially done.

**Unifying principle:** All genuine improvements from this research are instances of "capture more structured state at failure boundaries." RL systems instrument failure because they need reward signals. Agent loops should instrument failure because structured failure state is the only way to improve without gradient updates.

## Pattern 3: Function-Path Composability (validation, not actionable)

slime exposes 17+ `--custom-*-path` hooks. SkyRL's BasePPOExp requires overriding 3 methods for a new experiment. Both demonstrate that minimal interfaces make LLM-driven autonomous setup tractable. Confirms the design principle behind the loop skill's maker-checker split and the plan-as-data concept — not a new technique, but empirical validation.

## What Was Cut (forced analogies, documented to prevent re-derivation)

- **TrajectoryManager CLEAN/REALIGN/FORK drift classification → context management.** Token-level alignment technique doesn't transfer to semantic summary quality. Semantic drift requires LLM-as-judge, not token-ID comparison.
- **Optimizer-reset-after-weight-sync → convention invalidation.** No identifiable "momentum" in agent reasoning to detect/reset. The analogy sounds precise but generates no actionable design.
- **Multi-agent team reward → checker accuracy tracking.** Circular without an objective reward signal. Hermes has no oracle to verify checker accuracy against. Salvage: have the checker emit confidence levels and flag low-confidence verdicts.
