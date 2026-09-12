---
name: proactive-coach
description: The scheduled arm of the health coach — a weekly crunch over gathered data that emits at most one classified insight, plus the rules that decide whether to speak at all. Use when authoring any scheduled, cron or trigger-driven message, wiring a watcher, or running a weekly review.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [health, coaching, proactivity, cron]
    source: "arXiv 2605.06717 — Agentic Coding Needs Proactivity, Not Just Autonomy (Bui & Evangelopoulos, Google Labs, 2026)"
---

# Proactive Coach

## What this is

This is stages 6 and 7 of the coaching loop — **deliver** and **learn**. Everything upstream
imports, verifies and interprets data. This skill decides what, if anything, is worth
interrupting the user for, and then learns from how it landed.

Two failure modes bracket this skill:

- **A coach that never speaks is a report generator.** Silence is correct most of the time, but
  a system that is *always* silent is not coaching.
- **A coach that speaks constantly is noise.** Once the user starts ignoring messages, the
  channel is dead and the good insights die with it.

Holding that line is the entire job.

## The weekly crunch

Run weekly from a cron. The agent-driven paths (a cron whose prompt is the crunch) are the only
ones that can classify at runtime; a `no_agent` script delivers stdout verbatim and can only be
silent-unless-transition by construction.

1. **Collect** — pull the period's data: imports, prior ledger entries, and what changed in the
   user's profile or memory.
2. **Verify** — every number that drives an insight goes through `evidence-loop` first. Nothing
   enters interpretation unverified. This is the step that stops a plausible-but-wrong value
   becoming standing advice.
3. **Compare against the person's own baseline**, never a population norm. The user's own history
   is the reference frame.
4. **Draft** candidate insights — expect to discard most of them.
5. **Gate** each candidate (below).
6. **Emit at most ONE message**, classified.
7. **Ledger** what you sent.

If the crunch produces nothing that clears the gate, that is a successful run: ledger a silent
sweep and stop. Do not manufacture an insight to justify the schedule.

## The insight-quality gate

An insight is worth sending only if **every** one of these holds:

| Test | Question |
|---|---|
| **New** | Does the user already know this — from you, from their own senses, or from a message you sent last week? |
| **Actionable** | Can they do something differently because of it? |
| **Grounded** | Is it traceable to verified data, with no conclusion drawn from a single reading? |
| **Non-noise** | Does it survive the "so what?" test at 8am a week later? |
| **Timely** | Will it still matter when the message is read? |

Any failure → **SILENT**. Silence is the default and the most common correct outcome.

**Explicitly not insights** (each of these has burned someone):

- A single night's or single session's reading.
- A metric moving *within* its own normal range.
- Restating something the user told you this week.
- A trend you would need to hedge twice in the same sentence.
- Anything where the honest summary is "keep doing what you're doing".

## Classification — decide before delivery

Every proactive message is exactly one of:

- **ALERT** — time-critical, value decays in hours: breakage, data-loss risk, a monitored target
  hit, a safety-relevant result. Delivers immediately, any hour. Exempt from quiet hours **and**
  from pause.
- **DIGEST** — informational, value survives a night. Never delivers outside quiet hours. Queue
  to the next window; at show-time, if the insight has expired, drop it silently and ledger it
  as `dropped`.
- **SILENT** — the default. No message. Watchers should hash-suppress unchanged output so that
  content churn never becomes a notification.

Rubric: *loses value overnight → ALERT. Keeps value → DIGEST. Loses all value → don't send.*

## Quiet hours are configuration

Read the window and the timezone from config (e.g. `proactive.quiet_hours`, `proactive.timezone`).
**Never hardcode them**, and never infer the timezone from the host clock — hosts are frequently
UTC, and a naive hour check silently shifts the window. Default: 08:00–21:00 in the configured
timezone, pinned explicitly at every comparison.

## The outcome ledger

```bash
scripts/ledger.py add SOURCE CLASS HEADLINE   # → prints id; call AFTER the message is sent
scripts/ledger.py resolve ID acted|ignored|corrected|dropped
scripts/ledger.py report                       # per-source stats + recommendations
scripts/ledger.py pending                      # unresolved entries
```

- **Add when a message actually goes out.** Silence is free; speech is ledgered. In shell wiring,
  call it *after* the message with a guarded `|| true` — a failing ledger must never kill the
  delivery path.
- **Resolve at review time.** Whoever reviews (a session-end debrief, or the weekly crunch
  itself) runs `pending` and resolves: user acted or replied → `acted`; user corrected →
  `corrected` (also fix the cause); no reaction → `ignored`; dropped as stale → `dropped`.
- **Ambiguity resolves to `ignored`**, never `acted`. Desensitizing too early is recoverable;
  interrupting forever is not.

### Escalation

- **≥3 consecutive `ignored` DIGEST deliveries spanning ≥7 days** → pause candidate. The report
  *recommends*; a human confirms. A monitor the agent created may be paused by the agent; one the
  user requested requires asking. The 7-day span gate stops a holiday from killing a wanted
  monitor.
- **ALERT sources are never pause candidates.** Repeated ignored ALERTs mean the underlying
  failure is still unfixed — the report should say "fix the failure", not "pause the alert".

### Honest scope

This ledger measures **reply rate** — did the user react — not insight quality. It is a crude
proxy for the paper's Learning Lift, and it should be described that way rather than dressed up
as a quality metric.

## Pitfalls

- **`no_agent` scripts cannot classify at runtime.** Wire `ledger.py add` directly into the
  script's alert path, after the message, with `|| true`. Their only discipline is
  silent-unless-transition, so their trigger must be a genuine state change (target hit,
  breakage) — not content churn (title edits and metadata changes are not transitions).
- **Never pause an ALERT source.** Silence on a breakage watcher is how an outage goes unnoticed.
- **Ledger growth.** `report` prunes entries older than 90 days.
- **Never send two messages for one insight.** Pick the highest-value one; ledger the rest as
  considered-and-dropped so you do not re-derive them next week.

## Relation to the source paper

The action space here maps to the paper's `{notify, question, draft, stay silent}`: ALERT and
DIGEST are notify variants, SILENT is stay-silent. The ledger's acted/ignored/corrected stream is
a manual Learning Lift proxy measuring reaction rather than the paper's full insight-quality
metrics, and the escalation rule is the feedback-updated interruption policy (O3) in its crudest
deployable form.
