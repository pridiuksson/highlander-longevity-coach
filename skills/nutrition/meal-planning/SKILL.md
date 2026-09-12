---
name: meal-planning
description: Turn nutrition constraints and a day's shape into actual meals — day-type mapping, anchor-based structure, hard-constraint handling. Use when the user asks what to eat, wants a day planned, or must work around a constraint (no-cook, time, budget, intolerance).
license: MIT
---

# Meal Planning

## Scope (read this first)

Two skills are easy to confuse:

| Skill | Question it answers |
|---|---|
| `nutrition-advisory` | *Is this worth doing?* — evidence → recommendation |
| **`meal-planning`** | *What do I actually eat today?* — constraints → structure |

Meal planning does not re-litigate the evidence. If a recommendation is still contested, send it
back to `nutrition-advisory`; here it is an input, not a question.

## Step 1 — Establish the day's shape

Before naming a single food, get: training load and timing, meals at home vs out, time actually
available to cook, and appetite (hard training suppresses it — plan around that, not against it).

Classify the day:

| Day type | What changes |
|---|---|
| **Training day** | carbohydrate around the session; protein spread across the day |
| **Rest day** | lower energy emphasis; keep protein steady |
| **Travel / disruption day** | plans degrade — plan the *minimum viable* version instead |
| **Social day** | the meal is fixed by the occasion; plan the meals around it |

## Step 2 — Anchor, don't invent

Start from meals the person already eats, likes, and can repeat. A repeatable good-enough meal
beats an optimal one that happens once. Rotate a small set of anchors rather than generating new
recipes each time — novelty is the enemy of adherence.

## Step 3 — Build a meal: three slots

Every meal resolves to three slots:

1. **Protein anchor** — decide this first; it is the hardest to retrofit.
2. **Produce** — volume, fibre, micronutrients.
3. **Energy source** — carbohydrate or fat, chosen by day type (Step 1).

If time is short, drop to the *minimum viable meal*: protein + one produce item, eaten. Say so
plainly rather than presenting a plan that will not happen.

## Step 4 — Hard constraints are absolute

- **Allergies and diagnosed intolerances** are non-negotiable. Never propose an "exception", and
  never suggest "just a little".
- **No-cook / one-pan / batch** — match the constraint rather than arguing with it. Batch cooking
  is the default answer when time is the binding constraint.
- **Budget and availability** — plan against what is actually purchasable nearby.

## Step 5 — Output

Give the day's meals with portions, not a nutrition lecture. Mark which slot is flexible and
which is fixed. One line per meal; detail only where the user asked for it.

## Rules

- **Never invent nutrition numbers.** Source values from `swedish-food-nutrition` (grocery, café
  or packaged-label mode) or from the label in front of you. If a value is unavailable, say so
  instead of estimating silently.
- **Respect stated preferences** even where you disagree with them — flag the disagreement once,
  then plan within it.
- **Do not re-derive the evidence.** That is `nutrition-advisory`'s job.
- **Adapt to the person's own data**, never to a generic template: portions follow the user's
  body size, training load and goals from their health file.

## References

- `swedish-food-nutrition` — Swedish grocery/café/packaged source values.
- `nutrition-advisory` — which recommendations are actually supported.
