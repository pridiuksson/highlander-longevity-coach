# Demo catalog — per-skill demo recipes

Every entry: what it shows, `min_facts` (needed before it can run for real), and the learn-mode
`reward` (what gets executed the moment a fact arrives). Tier A = run live. Tier B = shadow
(pipeline + redacted docs, never fake data).

---

## Tier A — live

### swedish-food-nutrition — the flagship

- **Shows:** real grocery API, no auth, real prices right now.
- **min_facts:** none (defaults to Hemköp; better with `city` or store preference).
- **tour:** ask what protein staple they actually buy → `axfood.search()` it across Hemköp/Willys,
  show price per kg, name the skill out loud.
- **reward for `diet`:** price 3 protein staples matching the declared diet at the nearest chain.
- **reward for `city`:** pick the store chain actually near them.

### find-evidence — the credibility demo

- **min_facts:** a question the user genuinely has (ask for it — this is the free-text unlock).
- **tour/reward:** run the research funnel on THEIR question, show source tiers
  (official → retailer → secondary), report with citations and zero estimation.

### supplement-spec-verification

- **min_facts:** `supplements` list (even one product name).
- **reward:** verify their actual product's dose/form against Swedish retailer listings,
  flag reformulations.

### nutrition-advisory

- **min_facts:** `weight_kg` + `activity_level`.
- **reward:** compute their personal protein-target range, cite the guideline, offer to write it
  into `health.baseline_doc` Goals section.

### meal-planning

- **min_facts:** `diet` + one hard constraint (time budget, no-cook, intolerance).
- **reward:** plan one real day matching both, priced with swedish-food-nutrition at their store.

### deliberate / grill / peer-review / loop / plan

- **min_facts:** a real decision the user is weighing (the tour's second free-text question).
- **tour:** run `grill` (~2 min) on their actual decision — the null-hypothesis framing usually
  lands harder than any explanation. Mention `deliberate` for multi-domain health calls and
  `peer-review` as the 15-second reflex.

### ticket → work → commit → create-pr (workflow)

- **min_facts:** any repo on the box.
- **tour:** file a real `ticket` from something the user mentions, show how `work` executes an
  issue with zero conversation history. Only if the user is technical (learned from USER.md).

### schedule-management

- **min_facts:** pasted schedule text; Google Calendar auth for the sync leg.
- **tour:** parse a pasted week, flag conflicts, show the Calendar diff preview. Sync only with
  explicit consent; without auth, show what the parsed events would be.

---

## Tier B — shadow (never fabricate)

### garmin-import / samsung-health-import / wearable-health-data

- **Shows:** export → gated import → normalized `health.db` pipeline, using the skills' own
  redacted reference docs as the worked example.
- **Close with:** the exact command the user runs when they have the export, and the gate suite
  that must pass before any number is trusted.

### evidence-loop

- **Shows:** how a raw-data claim earns "vouched" status before it can become standing advice —
  the kit's core safety pattern. Demo the *concept* on a claim from find-evidence output.

### proactive-coach

- **Shows:** the weekly digest structure (empty-state, honestly labeled "this is the shape;
  yours starts after graduation + imports"), quiet hours, the one-classified-insight rule.
- **Reward for `sleep_window`:** show exactly which hours the digest will now avoid.

### eval-health

- **Shadow.** Meaningful only once the user cares about coach quality; mention, don't run.

---

## Learn-mode question ladder (highest value first)

1. `diet` (reward: priced staples) — cheap to answer, unlocks two skills
2. `city` / nearest store chain (reward: right store, right timezone for quiet hours)
3. A question they want answered, free text (reward: find-evidence run)
4. `weight_kg` + `activity_level` (reward: protein range) — PII, so only after rapport
5. `sleep_window` (reward: quiet-hours preview)
6. `supplements` (reward: spec verification)
7. Hard constraint for meal-planning (reward: a planned day)
8. `language` / reply style (reward: write it to USER.md, reply in it next message)

## State schema (`$HERMES_HOME/data/demo/state.json`)

```json
{
  "version": 1,
  "created": "<ISO-8601>",
  "facts": {"diet": {"value": "...", "provenance": "declared", "ts": "..."},
             "city": {"value": "unknown", "asked_at": "...", "skip_count": 1}},
  "asked_log": [{"fact": "...", "ts": "...", "outcome": "answered|skipped"}],
  "skip_streak": 0,
  "backoff_until": null,
  "budget_used": 0,
  "budget_limit_asks": 21,
  "budget_limit_days": 30,
  "stop_learning": false,
  "handoff": null
}
```

Rules: write via temp-file + rename (atomic); every write carries `version` for future
migration; `unknown` is explicit, never a default; `handoff` non-null = terminal state.

## Baseline doc contract

If `health.baseline_doc` does not exist, create it with the standard sections —
`## Measured values`, `## Constraints`, `## Supplements Stack`, `## Goals` — filled only with
learned facts; everything else `<unknown>`. If it exists, append into the matching section,
never restructure. Mirror the same facts into the `## Goals` line of
`~/.hermes/memories/USER.md` only when the user states a goal.
