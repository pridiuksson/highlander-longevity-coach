---
name: peer-review
description: "Quick gut check from a different LLM via command-code. Bounce ideas, catch blind spots, find simpler alternatives. Lighter than @grill. Invoke when you want a second opinion or a quick review of your ideas, plans or delivered work."
allowed-tools:
  - Bash
argument-hint: "<question-or-idea>"
---

# Peer-Review — Quick AI Gut Check

Bounce an idea off a different LLM. Quick sanity check, not deep adversarial analysis (`@grill`).

## Do this

Frame `$ARGUMENTS` as a prompt. The act of writing the prompt forces you to articulate what you're uncertain about — that's where the value is.

The peer runs from the project root and has full file access — reference files by path when helpful.

```bash
.agents/skills/peer-review/scripts/peer-review.sh "<YOUR_PROMPT>"
```

Set `cd` to the project root. Set `timeout_ms` to **300000** (5 minutes). If exit code is **2** (no CLI found), fall back to `spawn_agent` with the same prompt.

> **Headless pitfall (fixed 2026-09-20):** this script passes `--tools-all`. Without it a
> `command-code -p` run withholds tools and the peer replies "Shell is blocked in this session…"
> with **exit 0** — a non-review returned as success. If a peer reply is a single sentence with
> no file references or verdicts, treat it as FAILED and use the subagent fallback.

### After the peer replies

Report the peer's **main** insight in your own words. If you disagree, explain by bringing in YOUR verified facts based on evidence such as source code.

### Push-back discipline (validated 2026-09-21, reflect-loop PR)

The peer is a collaborator, not an oracle. When a peer claim conflicts with your reading:

1. **Reproduce the claim against a fixture before conceding.** One peer claimed a batch-resolve
   sweep would "manufacture" fast latencies; measured, it yields a ~168h median → `hold` — it
   *suppresses* acceleration. The peer conceded, and the actual manufacture path
   (same-session add+resolve) got a different guard (sample independence across delivery days).
   A measured push-back that relocates the fix beats blind acceptance *and* blind rejection.
2. **Build negative cases before asking for review.** Below-threshold, streak-reset,
   wrong-class inputs — not just the happy path. In the validating session the fixture suite
   caught the author's own bug (an ALERT branch set a reason but never set the action) before
   any peer saw the code.
3. **Time the review before the PR opens** when the change is consequential — review-after-ship
   turns findings into rework; review-before-ship turns them into the design.

### Follow-up rounds

- **CLI**: run `peer-review.sh` again with a follow-up prompt; up to **3** short rounds.
- **Subagent**: reuse `session_id` if your runner supports it.

## When

- Before planning — sanity check an approach
- During implementation — rubber-duck when stuck
- Before committing to a design — second opinion on trade-offs
- Before committing to a technology or architecture choice
- When reviewing skill or process changes
