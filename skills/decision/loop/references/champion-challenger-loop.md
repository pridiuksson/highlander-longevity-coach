# Champion-Challenger Loop Pattern

Adapted from 0xJeff's "Hermes Sensei Loop" (Jun 2026), originally sourced from Matthew Berman's Loop Library (signals.forwardfuture.ai).

## The Problem It Solves

The maker-checker split catches self-preferential bias: the checker verifies artifacts against the current spec. But it **cannot detect overfitting** — a solution that passes all current tests but fails on inputs it was never tested against.

Analogy: a junior analyst nails 14 practice deal memos, gets promoted, then applies the wrong pattern to a live deal because they memorized examples instead of learning principles. They overfit.

## The Pattern

**Champion**: The current best-known-good output/prompt. Holds the title until dethroned.

**Challenger**: A modified version that must prove itself on unseen data.

**Working set** (e.g. 14 examples): Test cases you edit against. The challenger practices here.

**Holdout set** (e.g. 6 examples): Test cases the challenger has NEVER seen. The promotion gate. This is the immune system against overfitting.

**Must-pass rules**: Hard invariants the challenger cannot break regardless of score.

**Promotion margin**: Challenger must beat champion on holdouts by a defined threshold (not just tie).

### Workflow

1. **Freeze the baseline** — Score the current champion on all examples. Split into working set + holdout set. Record scores.
2. **Fix ONE thing** — Pick a single recorded failure. Change only that. This is the challenger.
3. **Prove it on unseen data** — Test on working set first. If better, test on holdout set. Promote ONLY if holdout score beats champion by margin AND no must-pass rules broken.
4. **Stop when it stops improving** — Target score reached → ship. Budget exhausted → ship best champion. Two rounds with no holdout improvement → local maximum, stop tweaking.

### The One Rule

**Never promote on the working set.** If you do, you overfit — the solution gets great at the examples you're staring at and worse on new ones. Holdout promotion is mandatory.

## How This Extends Maker-Checker

| Dimension | Maker-Checker (current) | Champion-Challenger (new) |
|---|---|---|
| What it verifies | "Does output meet current spec?" | "Does output generalize beyond current examples?" |
| Overfitting detection | No | Yes — holdout set catches it |
| Regression detection | State regression only (artifacts undone) | Silent regression too (fixed one thing, broke another) |
| Stop condition | Convergence or stall | Local maximum (holdout plateaus) |
| Best-known-good tracking | No — latest wins | Yes — champion holds until dethroned |
| Use case | Single-task convergence | Recurring output quality improvement |

## Feedback Sweep Loop (Companion Pattern)

An automated collector that feeds into the Champion Loop:

1. Mines conversation/session history for user complaints and feedback
2. Organizes by workflow
3. Ranks by frequency ("you've complained about this 5 times")
4. Hands a prioritized fix-list to the Champion Loop

This replaces ad-hoc feedback with a structured pipeline: **collect → cluster → rank → improve**.

In Hermes terms: a cron job that runs `session_search` for negative feedback signals, clusters them by workflow, and writes a ranked backlog to a file the Champion Loop reads.

## When to Use Champion-Challenger vs Standard Loop

- **Standard loop (maker-checker)**: Single task, needs to converge, done when spec is met. e.g. "fix this bug", "write this script"
- **Champion-challenger**: Recurring output that should improve over time. e.g. "daily research cron quality", "prompt optimization", "report formatting"

The key test: if the output is generated once and done, use standard loop. If the output recurs and should get better each time, use champion-challenger.

## Local Maximum as Stop Condition

"Two rounds with no holdout improvement → local maximum, stop tweaking."

This is distinct from the stall detection in the main skill. Stall = no artifact change. Local maximum = artifacts keep changing but holdout quality stays flat. Different signal, same outcome: stop.

## Application to Cron Job Quality

The champion-challenger pattern maps naturally to Hermes cron jobs:

1. Each cron run produces output scored against must-pass rules
2. Periodically (weekly), a champion-challenger cycle runs:
   - Freeze current prompt as champion
   - Generate a challenger from the feedback sweep backlog
   - Test on holdout days (days the prompt has never been tuned against)
   - Promote or reject
3. Cron quality compounds over time without human micromanagement

## State File Extension

When running champion-challenger, extend `.loop-state.json`:

```json
{
  "champion": {"prompt": "...", "holdout_score": 0.82, "iteration": 3},
  "challenger": {"prompt": "...", "working_score": null, "holdout_score": null},
  "holdout_examples": ["unseen test case 1", "..."],
  "must_pass_rules": ["rule 1", "rule 2"],
  "promotion_margin": 0.05,
  "rounds_without_improvement": 0
}
```
