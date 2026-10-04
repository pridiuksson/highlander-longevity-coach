# Demo catalog — per-skill demo recipes

Every entry: what it shows, `min_facts` (needed before it can run for real), and the learn-mode
`reward` (what gets executed the moment a fact arrives). Tier A = run live. Tier B = shadow
(pipeline + redacted docs, never fake data).

---

## Tier A — live

(Live skills run on the user's actual question or inputs. Note: Wearable imports elevate to Tier A live ONLY if an export archive is already present on the box; otherwise they run as Tier B shadow.)

### swedish-food-nutrition (Track 2 Flagship: Metabolic & Nutrition)

- **Shows:** real grocery API, no auth, real prices right now.
- **min_facts:** none (defaults to Hemköp; better with `city` or store preference).
- **tour:** ask what protein staple they actually buy → `axfood.search()` it across Hemköp/Willys,
  show price per kg, name the skill out loud.
- **reward for `diet`:** price 3 protein staples matching the declared diet at the nearest chain.
- **reward for `city`:** pick the store chain actually near them.
- **Note:** DO NOT pitch to Track 1 (athletic/performance) users unless they explicitly ask about grocery pricing.

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

### stress-dialogue (Track 3 Flagship: Cognitive Appraisal & Stress Triage)

- **min_facts:** user mentions acute overwhelm, cognitive friction, or a deadline threat.
- **tour:** run `stress-dialogue` in text triage mode (`dialogue_triage.py --text "<USER_INPUT>"`); note that without telemetry flags, triage operates in text-appraisal mode. Show warm validation, structured appraisal, and commitment to exactly 1 tactical micro-action (`60-Minute Focus Boundary`, `Cyclic Physiological Sighing`, `Early Sleep Window`, or `5-Minute Grounding Pause`).
- **reward for `stress_pattern`:** run `dialogue_triage.py` on the friction context, previewing its classified appraisal quadrant and single recommended micro-action.

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

### apple-health-import / garmin-import / samsung-health-import / wearable-health-data (Track 1 Flagship)

- **Shows:** export → gated import → normalized SQLite pipeline, using the skills' own
  redacted reference docs as the worked example.
- **min_facts:** `wearable_hardware` (Apple Watch, Garmin, Galaxy Watch)
- **tour:** detect or ask which wearable they wear; show the SQLite schema, parse or preview RHR/HRV/VO2max/sleep pipeline.
- **reward for `wearable_hardware`:** configure ingestion pipeline and preview recovery metric baselines.
- **Close with:** the exact command the user runs when they have the export, and the gate suite
  that must pass before any number is trusted.

### biometric-recovery-ledger

- **Shows:** closed-loop outcome verification, tracking next-night autonomic rebound (HRV/sleep) after a coaching micro-action, filtering out alcohol, late dinner, bedtime drift, and heavy training confounders, requiring $N \ge 10$ unconfounded trials ($\Delta\sigma \ge +1.0$) for habit promotion.
- **min_facts:** `wearable_hardware` + an imported health database or completed triage event.
- **tour/reward:** preview the recovery ledger verification pipeline and unconfounded rebound delta tracking.
- **Close with:** `python3 skills/health/biometric-recovery-ledger/scripts/rebound_tracker.py auto-verify --event-id <EVENT_ID>` (turns live when export is ingested).

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

## Learn-mode question ladder (goal-conditional, highest value first)

### Track 1: Athletic & Performance
1. `wearable_hardware` (reward: initialize Apple/Garmin/Samsung ingestion pipeline)
2. `training_split` / current weekly volume (reward: concurrent training periodization review)
3. `weight_kg` + `activity_level` (reward: protein target range via `nutrition-advisory`)
4. A performance or recovery question they want answered (reward: `find-evidence` run)
5. `sleep_window` (reward: recovery digest quiet-hours preview)

### Track 2: Metabolic & Everyday Nutrition
1. `diet` (reward: priced protein staples at nearest chain)
2. `city` / nearest store chain (reward: right store, right timezone for quiet hours)
3. A food or biomarker question, free text (reward: `find-evidence` run)
4. `weight_kg` + `activity_level` (reward: protein target range)
5. Hard constraint for meal-planning (reward: a planned day)

### Track 3: Sleep, Stress & Deliberation
1. `sleep_window` (reward: quiet-hours preview and digest delivery scheduling)
2. A real decision the user is currently weighing (reward: `grill` or `deliberate` run)
3. `wearable_hardware` / recovery tracking preference (reward: HRV/RHR wearable tracking preview)
4. `evening_winddown_constraint` (reward: caffeine/screen cutoff schedule preview)
5. `supplements` / sleep stack (reward: spec verification via `supplement-spec-verification`)
6. `stress_pattern` / primary cognitive friction (reward: run `dialogue_triage.py` on the friction context, previewing its classified appraisal quadrant and single recommended micro-action)

## State schema (`$HERMES_HOME/data/demo/state.json`)

**No user facts live here.** The `facts` map is a *pointer ledger* only — where each fact was
written and when it was asked. The value itself lives in exactly one place (baseline doc for
health facts, USER.md for identity facts); state.json never stores the value, so there is no
second source of truth, no PII duplicate, and no drift.

```json
{
  "version": 1,
  "created": "<ISO-8601>",
  "facts": {"diet": {"stored_in": "baseline_doc", "ts": "..."},
             "city": {"stored_in": null, "asked_at": "...", "reoffer_at": null, "ask_count": 1,
                       "unreachable": false},
             "samsung-export-pitch": {"pitched_once": true, "ts": "..."}},
  "asked_log": [{"fact": "...", "ts": "...", "outcome": "answered|skipped"}],
  "skip_streak": 0,
  "backoff_until": null,
  "budget_used": 0,
  "budget_limit_asks": 21,
  "budget_limit_days": 30,
  "daily_ask_cap": 3,
  "tour_asks_today": {"date": "<YYYY-MM-DD>", "count": 0},
  "stop_learning": false,
  "handoff": null,
  "terminal": null
}
```

Rules:
- Write via temp-file + rename (atomic); every write carries `version` for future migration;
  unknown is explicit, never a default.
- **One terminal state**: `terminal` ∈ `graduated | stopped`, set together with `handoff` or
  `stop_learning` respectively. `graduated` beats `stopped` if both are somehow set. Any
  non-null `terminal` = the skill never asks again; `handoff`/`stop_learning` are kept only as
  provenance.
- `ask_count` per fact: a skipped question may be re-offered once — after 14 days, tracked via
  `reoffer_at`; a second skip sets `unreachable: true` (never asked again).
- **Tier-B pitches are tracked in the same facts map** with a `pitched_once` flag — each
  shadow-pitch happens at most once ever, then only on explicit user request.
- **Daily cap across modes**: tour questions and cron asks draw from the same
  `daily_ask_cap` (default 3/day total, = `demo.daily_asks` config), counted in
  `tour_asks_today` — so a tour session plus cron fires can never stack beyond the cap.
- **Graduation honesty rule**: declare "I know enough" only when the profile is actually
  complete (all facts in the ladder either stored or `unreachable`); if the budget expires
  first, the farewell says exactly that — "my question budget ran out — say `demo` whenever you
  want to continue" — never a false claim of completeness.

## Baseline doc contract

If `health.baseline_doc` does not exist, create it with the standard sections —
`## Measured values`, `## Constraints`, `## Supplements Stack`, `## Goals` — filled only with
learned facts; everything else `<unknown>`. If it exists, append into the matching section,
never restructure. Mirror the same facts into the `## Goals` line of
`~/.hermes/memories/USER.md` only when the user states a goal.
