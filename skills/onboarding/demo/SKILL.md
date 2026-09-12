---
name: demo
license: MIT
description: "Guided, hands-on tour of this kit for a fresh box: run real skills on the user's own questions, learn the user slowly (max 3 questions per session, skip always allowed), reward every answer with an immediately useful result. Also the daily learn-cron that retires itself at graduation."
version: 1.0.0
author: Hermes Agent
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [onboarding, demo, tour, personalization, cron, graduation]
    config:
      - key: demo.daily_asks
        description: "Max learn-mode questions per day (cron fires 1-2x/day, one question each)"
        default: "2"
      - key: demo.quiet_hours
        description: "Local window in which learn-mode may NOT ask questions"
        default: "22:00-09:00"
      - key: health.baseline_doc
        description: "Where learned health facts are written — the same file nutrition-advisory and the deliberation personas read"
        default: "~/health/baseline.md"
---

# Demo — Show it working, learn the user, get out of the way

A fresh adopter has 21 skills and zero data. This skill exists to close that gap by doing, not
describing: every demo is a **real skill run on the user's own input**, and every fact learned is
written **where the other skills already read**. When the profile is complete, this skill retires
itself and hands the user to `proactive-coach`.

Two modes:

| Mode | When | What it does |
|---|---|---|
| **Tour** | user says `demo`, or ONBOARDING step 10 | ≤3 questions (skip allowed) → run 1-2 live demos on the user's own question → close with their personal unlock path |
| **Learn** | daily cron (1-2 fires/day at random times) | ONE question per fire → instant useful reward computed from all facts known so far |

## Hard rules (all modes)

1. **Never fabricate data.** No synthetic watch data, no invented biomarkers, no fake exports.
   If a skill needs data the box does not have, the demo is *shadow mode*: show the pipeline and
   what the output will look like (structure, not numbers), then show the exact command the user
   runs when they have the real export.
2. **Facts go where other skills read — nowhere else.** Health facts (weight, diet, constraints,
   sleep window, supplements, goals) → `health.baseline_doc` (default `~/health/baseline.md`),
   using its existing section structure; unknowns stay `<unknown>` — never a guess.
   Identity/preference facts (city, language, role, reply style) → `~/.hermes/memories/USER.md`.
   Demo's own plumbing (budget, asked-log, skip-streak, handoff) → `$HERMES_HOME/data/demo/state.json`.
   **Nothing user-specific ever lands inside the skill directory or this repo.**
3. **Max 3 questions per session, skip always an option.** A skipped question is recorded as
   `unknown` with the date — it may be re-offered once after 14 days, never twice.
4. **No reward, no ask.** If no useful result is computable from facts-so-far, do not ask.
5. **Learn budget: 21 asks or 30 days**, whichever comes first, then stop — regardless of profile
   completeness. 3 consecutive skips → silent for 7 days. The user can always say
   "stop learning" and the cron retires immediately.
6. **Quiet hours respected** (`demo.quiet_hours`; when wiring the cron, reuse the same window
   set in step 5 for `proactive` so the two skills never speak in the same night).

## Tour mode — the demo catalog

Pick demos by what the user reveals. Full recipes with commands: `references/demo-catalog.md`.

| Tier | Skills | Demo style |
|---|---|---|
| **A — live** | swedish-food-nutrition, find-evidence, supplement-spec-verification, nutrition-advisory, meal-planning, deliberate, grill, peer-review, loop, plan, ticket/commit/create-pr/work, schedule-management | Run for real on the user's own question. Swedish grocery APIs work with no auth — this is the flagship "it just works" demo |
| **B — shadow** | garmin-import, samsung-health-import, wearable-health-data, evidence-loop, proactive-coach, eval-health | Show the pipeline + redacted reference docs; name the one export/command that turns it live. Label it clearly: "this runs when you have X" |

Tour session shape:

1. Check state; greet by what is already known (never re-ask).
2. Ask up to 3 questions — each chosen to unlock a demo (see catalog `min_facts`). Skip allowed
   on every one, no guilt.
3. Run 1-2 Tier-A demos **on the user's actual answer/question**.
4. Write learned facts to their homes (rule 2), update state.
5. Close with the **unlock path**: what works now → what one export/credential would add → what
   the system becomes in a month. One screen, no essay.

## Learn mode — the cron

Each fire (one question max):

1. Load state; if budget spent, skip-streak backoff active, quiet hours, or "stop learning" set →
   stay silent. Silence is a successful run.
2. Pick the highest-value unfilled fact whose **declared reward** is computable from facts-so-far
   (catalog: `min_facts` → `reward`).
3. Ask casually, offer skip.
4. On answer: write fact to its home (rule 2), then **run the reward immediately** — a real skill
   execution using everything known so far. Examples:
   - diet=vegetarian + city known → price 3 vegetarian protein staples at the nearest chain
   - weight + activity level → protein-target range via `nutrition-advisory`
   - sleep window → configure-and-preview what `proactive-coach`'s digest will respect
5. Update state atomically (see schema in the catalog reference).

## Graduation — the handoff contract

Profile complete **or** budget spent → write to state:

```json
"handoff": {"to": "proactive-coach", "ts": "<ISO-8601>", "facts": {"...": "..."}}
```

…tell the user **once** ("I know enough — from here you get the weekly digest instead of
questions"), and stop. Never re-ask anything after handoff. `proactive-coach` reads
`health.baseline_doc` and the imported databases directly — it needs no state from this skill,
so the contract is one-way and stateless on purpose.

## Updating

This skill is updated like any other in this kit (`cp -r`, ONBOARDING "Updating"). Because no
user state lives in the skill directory, an update can never lose what was learned — the
baseline doc, USER.md and `data/demo/state.json` all sit outside `skills/`.
