---
name: peer-review
license: MIT
description: "Use BEFORE acting on any unverified assumption or guess. Get a quick second opinion from a native Hermes subagent to catch blind spots and prevent confident errors."
version: 2.4.0
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [review, second-opinion, peer, sanity-check, subagent, delegate_task]
---

# Peer-Review — Quick Second Opinion (Native Subagent)

Bounce an idea off a native Hermes `delegate_task` subagent for a fast sanity check (not deep adversarial analysis).

> **Privacy / data handling:** Prompts and any context you include are sent to the **active model provider** for the subagent/session. **Keep sensitive health data and personal identifiers out of prompts unless the user explicitly agrees** to include them.

## Do this

**Before framing the prompt, fact-check what you can verify yourself.** Resolve verifiable claims from code, config, or actual output first. Frame the peer prompt around what remains genuinely uncertain (trade-offs, judgment calls, missing source-of-truth).

Write a short, specific prompt (aim for <100 words): the question, the decision point, and the key constraint. Reference file paths when helpful instead of pasting large or sensitive content.

### Run the peer as a native subagent

Use `delegate_task`:

```text
delegate_task(
  goal="You are a peer reviewer. Give a quick, honest second opinion on the question below. Do not rubber-stamp — flag blind spots, risks, and simpler alternatives. Keep it under 200 words.\n\nQUESTION:\n<paste your prompt here>",
  toolsets=["web"]
)
```

- The subagent starts with fresh context; include only the minimum necessary context (and file paths if needed).

### After the peer replies

Report the peer’s main insight in your own words, then critically evaluate — don’t rubber-stamp.

- **If the peer agrees:** push back with “What’s one specific way this could fail in practice?” before accepting.
- **If claims don’t hold up:** verify each against evidence (code/docs/behavior), challenge weak claims with the specific fact, and do a short follow-up round if needed.
- **Follow-ups:** up to 2–3 short rounds (push-back, or fix-then-confirm). Two is usually enough.

### Separated review (concerns vs solutions)

When reviewing a document that pairs concerns with proposed solutions, do two short reviews: (1) **concerns only** — right concerns, missing or overweighted? (2) **concerns + solutions** — do they close the concerns; which is weakest/overengineered?

## When to use

- Before acting on an unverified assumption or design choice
- Before planning/committing to a trade-off, when stuck or rubber-ducking
- Before/after building or porting skills (design pass, then implementation pass)
- For complex/high-stakes plans, pair with the **grill** skill for adversarial value/ROI stress-testing

## Pitfalls

- **Over-sharing sensitive data.** Don’t include health/personal data unless the user explicitly agrees; include only what’s needed.
- **Rubber-stamping.** Stress-test agreement; verify claims against evidence.
- **Long prompts.** Keep prompts short and specific.
- **Same-model blind spots.** A subagent is a second context but may share assumptions — verify important claims.

## Notes

Keep prompts short and include only the context needed for the judgment call (see privacy note above).
