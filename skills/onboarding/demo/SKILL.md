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
    blueprint:
      schedule: "30 10 * * *"
      prompt: >-
        Learn-mode fire for the demo skill. Load $HERMES_HOME/data/demo/state.json.
        If terminal is set, the budget is spent, backoff_until is in the future, the current
        local time is inside demo.quiet_hours (the NO-ASKING window — the inverse of the
        proactive skill's may-speak window, which must NOT gate this skill),
        or the shared daily ask cap (demo.daily_asks) is reached, do NOTHING — silence is a
        successful run. Otherwise pick the
        highest-value unfilled fact whose declared reward is computable from facts so far
        (skills/onboarding/demo/references/demo-catalog.md ladder), ask ONE casual question
        with skip offered, write the answer to its single home (health.baseline_doc or
        memories/USER.md), run the reward immediately, update the ledger atomically.
    config:
      - key: demo.daily_asks
        description: "Max questions per day across BOTH modes (tour sessions + learn cron draw from the same cap)"
        default: "3"
      - key: demo.quiet_hours
        description: "Local window in which learn-mode may NOT ask questions"
        default: "22:00-09:00"
      - key: health.baseline_doc
        description: "Where learned health facts are written — the same file nutrition-advisory and the deliberation personas read"
        default: "~/health/baseline.md"
---

# Demo — Show it working, learn the user, get out of the way

A fresh adopter has 22 skills and zero data. This skill exists to close that gap by doing, not
describing: every demo is a **real skill run on the user's own input**, and every fact learned is
written **where the other skills already read**. When the profile is complete, this skill retires
itself and hands the user to `proactive-coach`.

Two modes:

| Mode | When | What it does |
|---|---|---|
| **Tour** | user says `demo`, or ONBOARDING step 10 | ≤3 questions (skip allowed) → run 1-2 live demos on the user's own question → close with their personal unlock path |
| **Learn** | daily cron (blueprint ships one fire/day; a second optional fire may be added at setup), **one question per fire**. Each fire: (1) load state; if `terminal` set, budget spent, `backoff_until` in the future, inside `demo.quiet_hours` (the no-asking window), or the daily cap (`daily_ask_cap`, default 3/day shared with tour sessions) is reached → stay silent, silence is a successful run; (2) pick the highest-value unfilled, not-`unreachable` fact whose declared reward is computable from facts-so-far; (3) ask casually, offer skip; (4) on answer: write the fact to its single home (rule 2), then run the reward immediately (worked examples in the Learn-mode section below). |

## Hard rules (all modes)

1. **Never fabricate data.** No synthetic watch data, no invented biomarkers, no fake exports.
   If a skill needs data the box does not have, the demo is *shadow mode*: show the pipeline and
   what the output will look like (structure, not numbers), then show the exact command the user
   runs when they have the real export.
2. **Facts go where other skills read — nowhere else.** Health facts (weight, diet, constraints,
   sleep window, supplements, goals) → `health.baseline_doc` (default `~/health/baseline.md`,
   or wherever `skills.config.health.baseline_doc` points — read the config, don't assume the
   default), using its existing section structure; unknowns stay `<unknown>` — never a guess.
   Identity/preference facts (city, language, role, reply style) → `~/.hermes/memories/USER.md`.
   Demo's own plumbing — a **pointer ledger only** (which fact lives where, ask timestamps,
   budget) — goes to `$HERMES_HOME/data/demo/state.json`; fact **values** are never duplicated
   into state.json, so there is exactly one source of truth and no PII copy outside the homes
   the kit already uses. **Nothing user-specific ever lands inside the skill directory or this
   repo.**
3. **Max 3 questions per session, skip always an option.** A skipped question is recorded as
   `unknown` with the date — it may be re-offered once after 14 days, never twice.
   3b. **Daily cap across both modes**: tour questions and learn-cron asks draw from one shared
   cap (`demo.daily_asks`, default 3/day), counted in state — a tour session plus cron fires can
   never stack beyond it.
4. **No reward, no ask.** If no useful result is computable from facts-so-far, do not ask.
5. **Learn budget: 21 asks or 30 days**, whichever comes first, then stop — regardless of profile
   completeness. 3 consecutive skips → silent for 7 days. The user can always say
   "stop learning" and the cron retires immediately.
6. **Quiet hours respected** (`demo.quiet_hours`, default `22:00-09:00` — this is the
   *no-asking* window; it is the inverse of the `proactive` skill's *may-speak* window for
   digest delivery, which must NOT gate asking — do not copy that value in). When wiring the
   cron, schedule fires outside this window.

## Tour mode — the demo catalog

Pick demos by what the user reveals. Full recipes with commands: `references/demo-catalog.md`.

| Tier | Skills | Demo style |
|---|---|---|
| **A — live** | swedish-food-nutrition, find-evidence, supplement-spec-verification, nutrition-advisory, meal-planning, deliberate, grill, peer-review, loop, plan, ticket/commit/create-pr/work, schedule-management | Run for real on the user's own question. Swedish grocery APIs work with no auth — this is the flagship "it just works" demo |
| **B — shadow** | garmin-import, samsung-health-import, wearable-health-data, evidence-loop, proactive-coach, eval-health | Show the pipeline + redacted reference docs; name the one export/command that turns it live. Label it clearly: "this runs when you have X". **Pitch each Tier-B skill at most once ever** (tracked via the facts map's `pitched_once` flag, catalog §state) — after that, only if the user asks about it |

Tour session shape:

1. Check state; greet by what is already known (never re-ask).
2. Ask up to 3 questions — each chosen to unlock a demo (see catalog `min_facts`). Skip allowed
   on every one, no guilt.
3. Run 1-2 Tier-A demos **on the user's actual answer/question**.
4. Write learned facts to their homes (rule 2), update state.
5. Close with the **unlock path**: what works now → what one export/credential would add → what
   the system becomes in a month. One screen, no essay.

## Learn mode — the cron

The cron schedule itself is wired once during setup (ONBOARDING step 10) from the skill's
`blueprint:` frontmatter — a daily fire whose hour the scheduling agent jitters within the
allowed window (outside `demo.quiet_hours`, the no-asking window; never two asks within 4
hours). A second daily fire is optional; the blueprint ships one. `demo.daily_asks`
is the total daily ask cap shared by both modes (see rule 3b) — fires beyond what the cap
allows do nothing.

Each fire (one question max):

1. Load state; if `terminal` set, budget spent, skip-streak backoff active, quiet hours, or the
   daily cap (shared with tour sessions, `daily_ask_cap`) reached → stay silent. Silence is a
   successful run.
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

The **terminal state** is written when the profile is complete (every ladder fact stored or
`unreachable`) or the budget is spent — with an honesty rule: declare "I know enough" only if
the profile really is complete; if the budget ran out first, the farewell says that plainly
("my question budget ran out — say `demo` whenever you want to continue"). Write to state:

```json
"terminal": "graduated",
"handoff": {"to": "proactive-coach", "ts": "<ISO-8601>"}
```

(or `"terminal": "stopped", "stop_learning": true` if the user opted out). Tell the user **once**,
and stop — never re-ask anything after a terminal state. `proactive-coach` reads
`health.baseline_doc` and the imported databases directly — it needs no state from this skill,
so the contract is one-way and stateless on purpose.

## Updating

This skill is updated like any other in this kit (`cp -r`, ONBOARDING "Updating"). Because no
user state lives in the skill directory, an update can never lose what was learned — the
baseline doc, USER.md and `data/demo/state.json` all sit outside `skills/`.
