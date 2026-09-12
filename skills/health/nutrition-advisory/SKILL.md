---
name: nutrition-advisory
license: MIT
description: "Personalized nutrition and health research advisor. Filters research papers, supplement questions, and dietary advice through the user's blood biomarker profile. Use when: user shares a health/nutrition research paper (URL or PDF), asks about supplements (should I take X), asks about diet patterns (keto, Mediterranean, etc.), shares blood test results, or asks food-level questions. Applies profile-specific interpretation rules to prevent misreading biomarkers."
version: 1.3.0
author: <USER>
tags: [nutrition, health, research, supplements, bloodwork, diet]
---

# Nutrition Advisory — Personalized Health Research Filter

Every finding is evaluated against one question: does this apply to THIS person, with THESE markers, pursuing THESE goals? Generic nutrition advice is noise. The value is the PROFILE FILTER, not information retrieval.

## When to Use

- User shares a nutrition/health research paper (URL or PDF)
- User asks about a specific supplement ("should I take CoQ10?")
- User asks about a diet pattern ("is keto right for me?")
- User shares new blood test results for interpretation
- User asks a food-level nutrition question ("should I eat more berries?")
- User asks about interactions between supplements and their blood markers
- User describes what they actually eat day-to-day (dietary intake assessment — DIFFERENT from prescription)

## Process

### Step 1: Load Profile and History
Read `<YOUR_HEALTH_DIR>/health-profile.md` IN FULL. This is the lens. Cross-check mem0 (search "health profile" / "bloods" / "supplements") for any updates or corrections newer than the reference file. The reference file is the stable interpretive frame; mem0 has the latest values.

**Canonical source for supplement stack:** `$HERMES_HOME/$HERMES_HOME/personal/vitamins.md` (updated by the user's partner). The reference file's Supplement Stack section is a downstream COPY. If the user mentions supplement changes, or if the reference file seems stale, check the canonical source and sync both:
1. `<YOUR_HEALTH_DIR>/health-profile.md` — the skill's data layer (Supplement Stack table + Supplement Review Verdict section)
2. `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md` — the full health profile (Supplements Stack section)

When syncing: update the stack table AND the verdict section (move ADD items to ADDED, update DROP items, etc.). These are NOT symlinks — they are manual copies that drift.

**Source-of-truth files:** The canonical raw data lives in `<YOUR_HEALTH_DIR>/`:
- `<YOUR_BASELINE_DOC>.md` — original blood panels, supplement stack, fitness/sleep stats
- `<YOUR_NUTRITION_PLAN>.md` — food priorities by biomarker target (output of this skill)

`<YOUR_HEALTH_DIR>/health-profile.md` is a STRUCTURED COPY of that data. If they disagree, the reference file is the processed lens but `<YOUR_BASELINE_DOC>.md` may have newer raw data — reconcile by treating `<YOUR_BASELINE_DOC>.md` as ground truth for values and the reference file as ground truth for interpretation rules. See Step 2b for sync protocol.

Also scan `<YOUR_HEALTH_DIR>/research-log.md` entry headers for: (a) prior analysis of the same paper — if found, retrieve and confirm rather than re-analyzing from scratch; (b) prior conclusions on the same nutrient/biomarker/topic — required to populate the "Conflict with prior" field correctly and avoid contradictory mem0 entries.

**Food recommendation framework:** When the user needs meal structure (not just specific items), use `references/food-framework-no-cook.md` for the build-a-meal pattern (hunger tiers, category lists, day-type mapping, grocery staples). This is a reusable template, not session-specific data.

### Step 1b: Load Wearable Training Data (MANDATORY for training/recovery/sleep questions)

Before ANY advice touching training, recovery, sleep, or load: query `$HERMES_HOME/data/health.db` (see `samsung-health-import` skill for schema + verified mappings). Never reason from memory of past summaries — pull the series fresh.

Required queries for a training question:
1. Recent load: workouts last 4 weeks by type (minutes, frequency)
2. Recovery: nightly RMSSD (hrv_window, sleep-window avg) + RHR proxy (daily min of heart_rate min) last 2-4 weeks
3. Sleep: duration trend (sleep_session), NOT stage percentages (consumer-grade, 50-70% accuracy — see wearables-data-reliability.md)
4. Body: latest body_composition row (validated vs known: <YOUR_WEIGHT_KG> / <YOUR_WEIGHT_KG> skeletal muscle)
5. Data window: MAX(start_utc) across tables — state it in the answer; data ends at last export

Tier rules (advice-grade): RMSSD, RHR, sleep DURATION, workout minutes, body weight = TREND-RELIABLE (anchor advice here). VO2max (watch estimate) = LOW-CONFIDENCE — contradicts RMSSD+RHR trends; never advise from it alone. Stage splits = trend-indicative only. Zone thresholds (hr_threshold) drift month to month — read per-workout values, never assume.

For query patterns (night-keys, bout reconstruction, quartile enrichment, device-revision checks) and hard-won sqlite traps: `references/samsung-analysis-patterns.md`. Canonical runbook + confidence tiers + audit residuals: `<YOUR_HEALTH_DIR>/samsung-verified-data.md` — read before first advice on a fresh rebuild.

### Step 2: Fetch Research (if analyzing a paper)

Delegate to a subagent via `delegate_task`. NEVER fetch papers into own context — pollutes the context window.

Subagent extraction prompt should request:
- Bibliographic data (title, authors, journal, date, article type)
- Study design (type, sample size, population, duration, methods)
- Primary findings with specific numbers (effect sizes, CIs, ORs)
- Nutrients/foods/supplements discussed with doses and mechanisms
- Biomarkers discussed
- Population characteristics (age, health status — for applicability)
- Limitations stated by authors
- Conclusions / clinical implications

Extraction routing:
- **DEFAULT: subagent text extraction.** Covers ~90% of papers.
- **ESCALATE TO PDF:** paywalled/incomplete access, mechanistic pathway papers, critical dose-response tables, repeated reference papers.
- **ESCALATE TO VISION:** specific flagged figures only (dose-response curves, Kaplan-Meier plots, pathway diagrams). Never bulk figure extraction.

### Step 2b: If User Shares New Blood Test Results (not a paper)
1. Compare each marker to prior values in health-profile.md — note deltas and trend direction (Rule 9).
2. Check whether any Interpretation Rule's premise has changed (e.g., homocysteine now <10 → Rule 5 intervention succeeded; hsCRP now elevated → Rule 3 no longer fully applies).
3. Update health-profile.md Blood Test Results section with new panel. Update Active Targets & Retest Schedule. **ALSO update `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`** — this is the canonical raw record. If you don't update both, they drift (this already happened once: supplement review updated the reference copy but <YOUR_BASELINE_DOC>.md kept the old stack).
4. Log to research-log.md with Type: "Blood panel update" and note any rules whose status changed.
5. Write to mem0 ONLY if an interpretation rule's status changed (e.g., "TMG intervention succeeded — homocysteine <value>→<value> as of [date]").

### Step 2c: If User Shares Actual Diet (Dietary Intake Assessment)
This is fundamentally different from Step 2 (paper → prescription). This is mapping what the user ACTUALLY eats against their biomarker targets to find behavioral gaps. The prescription doc (`<YOUR_NUTRITION_PLAN>.md`) defines the target; this step measures the distance from it.

1. **Capture actual intake** — go meal by meal (breakfast → dinner). Store as an "Actual Diet — Observational Log" section in `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`. Self-reported, not tracked. Note meal timing (especially post-workout vs bedtime — these interact with recovery and sleep architecture).

2. **Map meals against biomarker targets** — for each meal, which of the 7 target categories (cognitive, ApoB, whole grains, methylation, magnesium, protein, iron) does it hit? Use the compression list from `<YOUR_NUTRITION_PLAN>.md` as the reference. Table format (meal × targets hit) reveals structural gaps instantly. Pattern matters more than individual foods: one strong meal doesn't cancel a protein vacuum at another.

3. **Challenge self-prescribed diet restrictions BEFORE accepting them.** If the user states they follow an approach ("low-carb," "low-fat," "keto"), check it against their own biomarkers. A metabolically healthy profile with a high training load has no biomarker reason to restrict carbohydrates — post-workout carbs serve glycogen replenishment and recovery. Push back when the stated approach conflicts with the bloodwork. This is often the single highest-value intervention in a diet assessment.

4. **Account for binding constraints.** "Doesn't cook," "no time in mornings," "eats at buffets" are real constraints that determine whether a recommendation is executable. Solutions must work within them — recommend no-prep protein (existing supplements like casein powder, cottage cheese, tinned fish, vacuum-packed lentils, protein bars/puddings/kvarg) rather than recipes. NOTE: "batch-boil eggs" requires cooking — it violates the no-cook constraint. Hard-boiled eggs from a grocery store deli counter are fine; boiling them yourself is not. Check each protein source against the binding constraint before recommending. A recommendation the user can't execute is worse than no recommendation.

5. **Provide frameworks, not single items, when the user lacks structure.** The user explicitly stated: "I'd eat more good food, I just lack structure for what is good for me. I am not lazy, I am unstructured and you're to help." When the user asks for food help, they want SYSTEMS they can follow independently — not just "grab X." Provide:
   - **Build-a-meal frameworks** organized by hunger level (tiers: not hungry / hungry / very hungry) — see `references/food-framework-no-cook.md` for the template pattern
   - **Category-based food lists** (pick 1 protein + 1 carb + 1 fat) rather than fixed meal prescriptions
   - **Day-type mapping** (which tier applies on which training day — Monday interval day needs more fuel than Sunday rest day)
   - **A grocery list of staples** to keep stocked at home

   Do NOT default to "lowest-friction single item" recommendations (e.g., "just grab a shake") when the user has expressed they want real food and are willing to eat well. The right answer to "what should I eat post-gym" is a tiered framework with 5+ options, not "Muscle Up smoothie every time." The user prefers real food (sandwiches, salads, cold assembly) over yet another shake — they already have a pre-gym casein shake and don't want three liquid meals in one evening.

6. **Flag cumulative exposure risks across meals.** Foods eaten daily across multiple meals stack exposure differently than the same total eaten once. Smoked/cured fish (salmon) at both lunch AND dinner = daily nitrite/nitrosamine load — IARC class 1 carcinogen, same category as processed red meat. Recommend fresh fish rotation when cured products appear more than 3×/week total.

### Step 2d: Verify Actual Supplement Intake (MANDATORY Before Dosing Analysis)

Before analyzing supplement dosing, interactions, gaps, or building ANY theory that depends on what the user consumes, produce an "Actual Daily Intake" table that separates products into Daily / Intermittent / Stash categories. If you don't know which products are actually consumed, ASK before analyzing.

This step exists because in a prior session the agent:
1. Built a caffeine/HRV suppression theory assuming daily pre-workout use — user didn't take it at all ("just in stash").
2. Calculated TMG dosing assuming both the B-complex AND standalone TMG were active — standalone had just been bought and wasn't in routine yet.
3. Was corrected twice on the same assumption in one session.

The anti-pattern was already documented. It was violated anyway. Promoting it to a mandatory process step is the structural fix. **Inventory ≠ intake. A 13-product stash may mean 8 products are daily drivers and 5 are shelf-sitters. Do not build on assumptions.**

**Step 2d.1 — Verify product specs against manufacturer pages.** User-recalled doses are frequently wrong in both directions, and record files carry spec errors. Before any interaction or upper-limit analysis, delegate a spec-verification pass against the official product pages (retailer nutrition tables are acceptable when two or more agree; note the full ingredient list). Error classes this catches: (a) label-identity errors, where the user names a different product than the one they take, changing the dose by an order of magnitude; (b) record-file errors, where a "per serving" column is read as "per capsule" (or the per-2-cap column as per-1) and every downstream total is wrong; (c) undisclosed co-formulations that change interaction and timing rules. RULE: when a label shows a "per serving" column, determine the units-per-serving BEFORE recording any spec.

**Step 2d.2 — Sum co-formulated actives across the WHOLE stack against upper limits.** Different products in the same stack often share an active, and each looks reasonable in isolation while the total exceeds the upper limit (B6 is the classic case: a B-complex plus a mineral capsule can cross the EFSA tolerable upper limit even though neither product is high-dose on its own). Do the upper-limit arithmetic on STACK TOTALS, never per-product. A dosing-frequency change (e.g. every-other-day) is a valid fix — but check that halving one active does not break the therapeutic dose of the OTHER actives in the same product.

### Step 3: Filter Through Profile
Apply interpretation rules from `<YOUR_HEALTH_DIR>/health-profile.md` (Section: Interpretation Rules). Weigh evidence quality. Classify findings into action tiers.

### Step 3b: Identify Missing Data (for comprehensive health assessments)
When doing a full-profile review (not a single-paper analysis), use `peer-review` to stress-test for blind spots. Frame the prompt with the full profile context and ask: "what are the most important MISSING data points that would redirect strategy?" The peer catches gaps you're blind to (e.g., blood pressure — the #1 CV risk factor, never measured; training program structure; caffeine timing). Critically evaluate the peer's output — discard over-engineered claims (e.g., Lp(a) particle concentration when mass is already well below threshold) and keep genuinely redirecting insights. See the peer-review skill for the push-back protocol.

### Step 4: Output
Present tiered analysis. Then persist conclusions per persistence rules.

## Evidence Quality Weighting

Soft hierarchy. Agent reasons about modifiers in 1-2 sentences per paper. NEVER uses numeric scoring.

**Hierarchy (strongest to weakest):**
1. Meta-analysis / systematic review (Cochrane, JAMA meta)
2. RCT in humans
3. Prospective cohort study
4. Cross-sectional study
5. Mechanism / animal / in-vitro — HYPOTHESIS-GENERATING ONLY

**Modifiers to reason about:**
- Sample size and effect size (clinically meaningful, not just statistically significant?)
- Replication (single study vs confirmed by independent groups)
- Population match (healthy middle-aged males? or sick/elderly/different sex?)
- Recency (nutrition science moves; >5 years = flag for updates)
- Funding source / conflicts of interest

**Mechanism papers** (mice, cell lines, biochemical pathways) are NEVER actionable on their own. They generate hypotheses. Automatically classify as SKIP unless backed by human trial data in the same analysis. A paper studying only sick/elderly/sedentary populations may not apply to a metabolically healthy, highly active 40yo male — flag this mismatch.

## Source Attribution (MANDATORY on every recommendation)

Every food, supplement, or behavior recommendation MUST cite its source. No exceptions. The user needs to know WHERE each piece of advice comes from so they can weight it — and so future papers can upgrade or overturn it.

### Source Tiers (strongest to weakest)

1. **[PAPER: Author Year]** — from the paper currently being analyzed. Strongest for this run. Evidence quality assessed per the ladder above.
2. **[PRIOR: Author Year]** — from a previously logged paper in research-log.md. Carries that paper's evidence quality assessment forward. Must scan the log in Step 1 to cite these.
3. **[PROFILE: Rule N]** — derived from the user's blood markers / health-profile.md interpretation rules. High personal relevance (it's YOUR blood), but mechanism-based — not a clinical trial proving the food fixes the marker. Be honest about this distinction.
4. **[GENERAL]** — general nutrition knowledge NOT backed by a specific cited source in the log or the current paper. WEAKEST. Must be flagged explicitly. The goal is to minimize these over time as papers fill the gaps.

### How to Apply

- Tag each DO, KEEP, and SKIP item with its source tier in brackets.
- Items can have MULTIPLE sources: `[PAPER: Tessier 2025] + [PROFILE: Rule 5]` means the paper provides the pattern and the profile provides the personal relevance.
- A `[GENERAL]` tag is a flag to the user: "I have no specific paper for this — it's common knowledge." This is honest, not embarrassing. But the user should know which recommendations would benefit from research backing.
- When synthesizing across multiple papers (future), rank recommendations by the strength of their accumulated sources. A food backed by two cohort studies outranks one backed by general knowledge alone.

## Output Format

### Three Action Tiers

Each item tagged with source attribution (see Source Attribution section):

- **DO [SOURCE]** — specific change to make based on this finding (start/stop/reorder/timing change). Must be concrete enough to act on tomorrow.
- **KEEP [SOURCE]** — confirms current protocol is right. This is HIGH-VALUE output, not a footnote. It gives confidence to maintain a regimen.
- **SKIP [SOURCE]** — irrelevant to this profile, too weak to act on, wrong evidence level, or addresses a problem the user doesn't have.

### Phased Implementation (MANDATORY for multi-domain changes)

When the output involves changes across training, nutrition, supplements, and lifestyle simultaneously, do NOT present all changes as a single "do this starting tomorrow" block. The user explicitly prefers: "step by step, not an instant revolution." Structure as:

1. **Phase 1 (Week 1-2):** Only the highest-ROI changes (1-3 items). No new habits requiring willpower. Architectural fixes only (e.g., "walk into the store you already pass").
2. **Phase 2 (Week 3-6):** Layer in training changes one piece at a time.
3. **Phase 3 (Week 7+):** Optional optimizations based on adaptation.

Each phase must be survivable if the user stops after it — no phase should depend on the next one to make sense. State what NOT to do in each phase explicitly.

### Training Psychology — Account for Engagement

When advising on training programs, account for the user's psychological need for intensity variety. An optimized polarized program (80% Zone 2 + 20% Zone 5) will fail if the user finds the easy days "very boring" and has no hard session to look forward to. The fix is not to eliminate easy days — it's to make the hard days genuinely hard (Norwegian 4×4 intervals, not lukewarm tempo). Frame the contrast explicitly: "Monday is your suffering day. Saturday being boring is what buys Monday's quality." Never prescribe a training structure where every day is medium-hard — that's the gray zone that produces fatigue without adaptation. CORRECTION (2026-08-15): this section previously claimed gray-zone training "caused VO2max decline from <value>→<value> in this user" — that decline was RESOLVED as a device artifact (Samsung max-HR re-anchoring <value>→<value>; cliff landed 60 min after a revision, same day, while RMSSD/RHR improved). Never cite the watch VO2max decline as evidence for any training claim; see `references/samsung-analysis-patterns.md`. The engagement principle stands on its own merits.

### Additional Output Elements

- **EVIDENCE QUALITY** — 1-2 sentences on where this paper sits on the ladder and why. State if population match is weak.
- **CONFLICT** (if applicable) — finding contradicts a prior conclusion. Surface both. Do NOT silently overwrite. Require the newer paper to be BOTH stronger evidence quality AND population-relevant before overturning. Otherwise flag as "investigate further."
- **WHAT THIS CANNOT DO FOR YOU** — always explicit. What gaps remain, what biomarkers weren't measured, what timescales are out of scope.

Tiers are heuristic defaults, not straitjackets. "This paper is noise for you" is a valid and valuable answer.

## Persistence Rules

### Step 1: Write to Research Log (ALWAYS)
Append one entry to `<YOUR_HEALTH_DIR>/research-log.md` per paper analyzed. Format:

```
## [Author lastname] [Year] — [Short title]
Source: [Journal, DOI/URL] | Analyzed: [Date]
Type: [Meta-analysis / RCT / Cohort / Mechanism / Blood panel update / etc.]
Evidence quality: [1-2 sentences with population match assessment]
DO:
  - [item] [SOURCE: PAPER/PRIOR/PROFILE/GENERAL]
KEEP:
  - [item] [SOURCE: PAPER/PRIOR/PROFILE/GENERAL]
SKIP:
  - [item] [SOURCE: PAPER/PRIOR/PROFILE/GENERAL]
Scope limits: [what this CANNOT do for this profile — biomarkers not measured, outcomes not covered]
Conflict with prior: [yes/no — if yes, what]
Overturned prior: [yes/no — if yes, what conclusion was replaced and why]
mem0 facts written: [N]
```

Write to log FIRST. Always — even if nothing actionable. The log captures what DIDN'T change, which is as valuable as what did.

### Step 2: Write to mem0 (CONDITIONALLY)
After writing to log, extract conclusions to mem0 ONLY if there are DO or KEEP items.

**Decomposition axis:** one fact per biomarker, intervention, or behavior. Never overlap. "Creatine helps cognition" and "creatine improves working memory" are ONE fact.

**No-evidence path:** if paper yields nothing in DO or KEEP, write ONLY the log entry. Do NOT write to mem0. Zero-signal entries degrade retrieval quality for everything else.

**Format:** state the conclusion, the source, and why it applies to this profile. Example: "AHEI is <USER>'s reference diet pattern — Tessier 2025 (Nature Medicine, 105k cohort) showed AHEI outperformed Mediterranean/DASH/MIND for healthy aging."

**Conflict cleanup:** when a new conclusion overturns a prior one (per the conflict resolution protocol), update the old mem0 fact rather than adding a contradictory one. Search mem0 for the old conclusion, replace it with the new one noting the supersession ("Supersedes prior recommendation from [source] — [date]").

## Anti-Patterns

- Do NOT fetch papers into own context — always delegate to subagent
- Do NOT store raw paper content in mem0 — store filtered conclusions only
- Do NOT treat mechanism/animal papers as clinical evidence
- Do NOT apply generic nutrition advice — everything is filtered through the profile
- Do NOT re-explain the process each session — this skill IS the process
- Do NOT interpret creatinine-based eGFR as kidney function for this profile (creatine artifact)
- Do NOT recommend insulin-sensitizing interventions without flagging the user has no insulin resistance
- Do NOT accept user's self-prescribed carb/fat restriction without checking against biomarkers — metabolically healthy athletes (Rule 4) restricting carbs post-workout are leaving glycogen recovery on the table for no metabolic reason
- Do NOT prescribe uniform carb targets when training includes both resistance and endurance — use CARB PERIODIZATION by day type. When a user does both lifting and zone 3 runs (tempo/threshold intensity), the resolution to "should I eat carbs?" is not binary. Periodize: run days need 5-7g/kg (zone 3 depletes 110-260g glycogen per session, heavily carb-dependent), gym days need 3-5g/kg, rest days can stay lower. A single banana (~25g carbs) is <10% of the glycogen deficit from one zone 3 session — dangerously inadequate for endurance recovery but fine as a gym-day pre-workout top-up. The user's low-carb identity does not need to be dismantled — it needs to be scheduled around the 2 run days. In a 4-expert deliberation, the pragmatist correctly flagged that prescribing 340-476g carbs/day to a takeout eater is behaviorally impossible, but all 3 other experts agreed the "one banana" alternative was physiologically dangerous. The resolution: periodize by day type, keep total amounts achievable, and let glycogen needs drive the run-day increment
- Do NOT overlook cumulative exposure to cured/processed foods across multiple meals — daily smoked salmon at both lunch and dinner stacks nitrite/nitrosamine load. NOTE: Nordic smoked salmon is IARC Group 3 ("not classifiable"), NOT Group 1. Only Chinese-style salted fish is Group 1. Processed mammalian meat is Group 1. The distinction matters — don't overstate the evidence. The health-protective instinct to limit cured fish and rotate with fresh fish is reasonable, but the IARC classification must be stated accurately. Recommend fresh fish rotation when cured products appear more than 3×/week total
- Do NOT conflate "same ingredient in two products" with "duplication" — check DOSES before calling something redundant. Two products can share an active ingredient at different doses serving different therapeutic purposes. Example from a 4-expert deliberation: the pragmatist recommended cutting a TMG standalone (500mg/cap) because "it duplicates the B-complex" — but the B-complex only has 200mg TMG. Cutting the standalone would have left the user at 200mg/day, which is ~10× below the 1.5g minimum effective dose for homocysteine lowering. The error was caught during Phase 2 critique and corrected. Rule: before calling two products duplicative, compare the actual mg of the shared active ingredient and the therapeutic dose range. Same ingredient ≠ same dose ≠ same purpose
- Do NOT recommend foods requiring daily cooking — the user batch-cooks 2-3×/week (quinoa, grains, eggs) but will NOT cook on training days. "No-cook" applies to daily meal prep; batch-cooked fridge portions are fair game. Dry quinoa (batch-cooked) is preferred over expensive pre-cooked packs
- Do NOT recommend antioxidants/anti-inflammatories without flagging the user has minimal inflammatory substrate. CRITICAL for athletes: high-dose antioxidants (vitamins C/E, curcumin) **blunt exercise adaptations** — they block training-induced mitochondrial biogenesis and insulin sensitization via mitohormesis (Ristow et al., PNAS 2009). This is the strongest argument against turmeric/curcumin for an athlete — stronger than "no inflammation signal." The adaptation-blunting rationale was lost during a document restructuring and had to be re-discovered. When cutting an antioxidant supplement, record the adaptation-blunting reason alongside the inflammation rationale — both arguments must be preserved or the decision gets re-litigated
- Do NOT propose supplements without checking the current stack in `<YOUR_HEALTH_DIR>/health-profile.md` first
- Do NOT assume supplement stack inventory = daily consumption. A 13-product stash does not mean 13 products are taken daily. Before analyzing dosing, interactions, or gaps, ASK which products are actively consumed vs. sitting in stash. Building analyses (caffeine load, TMG dosing, redundancy) on products the user doesn't actually take produces confident-sounding nonsense and erodes trust. The user's correction: "You do not assume I mindlessly eat all the stuff every day." This was violated TWICE in one session (pre-workout caffeine theory built on stash-only product; TMG dosing analysis based on standalone product not yet in routine). The fix: explicitly ask "which of these do you actually take daily?" before ANY dosing analysis.
- Do NOT build optimization protocols against consumer wearable data without flagging its accuracy limits. Samsung Galaxy Watch / similar wearables estimate sleep stages at 50–70% accuracy vs polysomnography. Deep sleep percentages, sleep latency, and REM estimation are SOFT data — they're trend-indicative but not precise enough to optimize against. An entire deep-sleep improvement protocol (temperature manipulation, timing changes) was built and then retracted because the underlying watch data wasn't reliable enough to support it. When using wearable data: trust total sleep time, HR, HRV as trend indicators. Do NOT trust stage-level breakdowns (deep %, REM %, latency) as optimization targets. If the user says their device may have accuracy issues, STOP building protocols against it immediately.
- Do NOT reference activities or routines as ongoing without confirming they're current. A user who did hot yoga Jan–Mar and stopped in March was repeatedly told "your yoga practice" and had protocols built around ongoing yoga — twice — requiring user correction both times. Before referencing any activity pattern in advice, check whether the pattern is CURRENT or historical. Annual aggregate data (e.g., "23h hot yoga YTD") does NOT mean the activity is ongoing — it could all be front-loaded in a period that has ended. When in doubt, confirm: "Are you still doing X?"
- Do NOT establish a biomarker trend from values measured at different labs without checking assay comparability. Inter-assay variation alone can produce an apparent trend, so two points from non-comparable assays cannot support a slope. When markers come from different labs: (1) flag the cross-lab artifact explicitly, (2) do NOT project a forward trajectory until a same-lab repeat confirms it, and (3) if an earlier analysis concluded "no action", downstream documents must preserve that conclusion — quietly drifting to a more aggressive threshold in a later document without re-analyzing is a provenance failure. The same discipline applies to single readings: establish the TREND (monthly/annual average) before assessing any individual value. Individual points are noise; the trend is signal.
- Do NOT model ferritin in isolation from training load and meal timing. Iron status in an endurance athlete is a multi-factor trajectory: (1) foot-strike hemolysis scales with running volume, (2) training raises hepcidin for hours post-exercise, and hepcidin blocks intestinal iron absorption for up to a day, (3) chronic under-fuelling amplifies the hepcidin response (the RED-S pathway), (4) sweat iron losses increase with training. When iron stores are falling while training load is RISING, project the trajectory rather than reading one value. Low-cost interventions that are easy to miss: (a) time iron-rich meals for MORNING/breakfast, away from the post-exercise hepcidin window, (b) pair with vitamin C (a large absorption boost for non-heme iron), (c) keep coffee/tannins out of the 30–60 min BEFORE an iron-containing meal, (d) do NOT supplement iron prophylactically before a confirmed deficiency — gastrointestinal side effects and oxidative cost outweigh the benefit while stores are adequate. CRITICAL: the coffee/iron interaction is ACUTE (a window around the meal). Do not claim that coffee hours earlier or the next day blocks iron absorption; the real concern is coffee consumed shortly BEFORE an iron-containing meal. A caffeine cutoff imposed for SLEEP is a separate concern — do not conflate the two.

### Consumer Wearable Data — Accuracy Limits
When working with Samsung Galaxy Watch or similar consumer wearable data, consult `references/wearables-data-reliability.md` for which metrics are trend-reliable vs optimization-grade. Key principle: total sleep time, HR, HRV = trend-reliable. Deep sleep %, REM %, sleep latency, BIA body composition = NOT precise enough to build protocols against. Never build an optimization protocol that depends on the precision of a single wearable metric. **This is now a mandatory process step — see Step 1b. The anti-pattern was present and was still violated twice; promoting it to a process step is the structural fix.**
- Do NOT build physiological intervention theories on insufficient or stale data. A deep-sleep optimization plan was built on March/April samples (46–77 min deep, 9–15%); current June data showed 84–90 min deep at 20–22% (elite). The "problem" didn't exist — the data was old. Before proposing interventions: (1) verify the data is CURRENT, (2) require ≥3 data points from the same period, (3) check whether the theory is consistent with ALL available data. If existing data contradicts the theory, acknowledge the contradiction immediately — do not rationalize around it.
- Do NOT classify workout intensity from a single heart rate zone model without checking for alternatives. Consumer fitness devices (Samsung Watch, Garmin) often display MULTIPLE zone models simultaneously — a standard 5-zone model (% of max HR) and a threshold-based model (AT/AnT). These give CONTRADICTORY classifications of the same workout: in one session, a <YOUR_RESTING_HR_BPM> avg run was classified as "Zone 3" (standard model), "Zone 2" (AT/AnT model), and "Zone 2" (Karvonen formula) — three different answers from three models. The agent flip-flopped across three responses before the user asked for a cross-check. The fix: (1) identify the user's AEROBIC THRESHOLD as the physiological dividing line (Samsung estimates this as "AT" in the zone breakdown view), (2) classify based on whether avg HR is above or below AT — not on which arbitrary zone label the device assigns, (3) when the user provides workout data, request ALL zone views/screenshots BEFORE classifying. If only one view is available, state which model you're using and flag the uncertainty. For trained athletes with low resting HR (<YOUR_RESTING_HR_BPM>), standard % of max HR zones are inaccurate — use Karvonen or threshold-based zones instead
- Do NOT accept external supplement or health recommendations (from apps, platforms, doctors, nutritionists) without cross-checking them against the user's actual biomarker gaps. When auditing an external recommendation set: (1) map each recommendation to the biomarker it targets, (2) check whether that biomarker is a real gap or already optimal, (3) flag conflicts with the user's training goals (e.g. AMPK activators such as berberine antagonise mTOR and conflict with hypertrophy; high-dose antioxidants can blunt exercise adaptations), and (4) identify what the recommendation set MISSED. A list that fires on the healthiest part of a panel while ignoring the real gaps has pattern-matched on marketing, not on the data.
- Do NOT silently override a physician's recommendation or a prior analysis when they conflict — document both and let the user decide. The correct response is not to pick a side quietly: (1) record both positions with their evidence, (2) present both honestly, (3) add practical timing/interaction rules regardless of which way the user goes, and (4) acknowledge that the clinician examined the patient in person — clinical judgement from physical examination carries weight that lab-value analysis alone cannot match. A prescription given "for performance, not pathology" uses a different risk-benefit framework than treating a biomarker gap; say so explicitly. The user decides between clinical authority and analytical depth.
- Do NOT miss geography-specific nutrient gaps that don't appear in blood panels. Swedish soil is notoriously selenium-poor — Nordic populations are universally suboptimal. The 4-expert deliberation missed selenium because it wasn't in the blood panel, but a physician's CoQ10 product happened to include 55µg selenium, which was the hidden win of the prescription. Always scan for known geographic deficiencies (Scandinavian selenium, Nordic winter vitamin D, iodine in inland populations) even without blood test confirmation. These are population-level gaps, not individual biomarker questions.
- Do NOT keep multiple BioPerine (piperine) sources in the supplement stack simultaneously. Piperine non-specifically inhibits CYP3A4 and P-glycoprotein, altering absorption of ALL co-ingested substances. When a new supplement containing BioPerine is added (e.g., physician-prescribed CoQ10 with BioPerine), DROP other BioPerine sources (e.g., turmeric/curcumin with BioPerine). Rule: one BioPerine source maximum, taken 2h isolated from other supplements. Two piperine sources double the pharmacokinetic interference without doubling the benefit. REFINEMENT (2026-08-15 peer review): the isolation requirement applies to CO-INGESTION only — piperine's Tmax is 1-2h and its in-vivo human effects (curcumin, diclofenac) all involve simultaneous presence. For nutrients with no in-vivo piperine-interaction evidence (D3, omega-3, Mg-bisglycinate, TMG — peptide/transporter pathways, not CYP/P-gp substrates), a 2h gap is over-engineering; a separation of a few hours is comfortably sufficient. Don't build elaborate isolation schedules where a simple "different meal" rule suffices.
- Do NOT anchor supplement timing to meals the user might skip (2026-08-15 lesson). A schedule built on "AM with breakfast" collapses when breakfast is variable/skipped. Anchor instead to the user's INVARIANT meals (e.g., 12:30 lunch = the one guaranteed meal; post-training food before a hard cutoff). Identify invariants by asking for the actual weekly schedule — wake time, work hours, training window, LAST-food cutoff — before placing any timed dose. A supplement timed to a meal that happens 50% of the time is taken 50% of the time.
- Do NOT design monitoring plans around scheduled blood draws without confirming the user's actual draw budget (2026-08-15 lesson: draws are expensive + time-consuming for this user). Design draw-lean: (1) pre-committed decision rules must be DRAW-DATE-AGNOSTIC — they fire at "next draw, whenever it is," never "week 12"; (2) resolve borderline results with a co-measured tiebreaker from the SAME draw (e.g., LDL for borderline ApoB — LDL moves ~2× the relative magnitude of ApoB, so it disambiguates ApoB-LDL decoupling) instead of ordering a repeat draw; (3) one comprehensive tiered panel (decision-critical markers → nice-to-have → skip) beats a calendar of small draws; (4) between draws, run the watch-driven interim loop (HRV/RHR/sleep/performance proxies) as the PRIMARY feedback, not the backup.
- Do NOT accept external training programs (from PTs, coaches, apps) without verifying modalities and intensity zones against the user's actual physiology. Pattern from a PT consultation review: (1) The PT prescribed Zone 5 intervals "adapted for running" but the attached template PDF revealed 3 of 4 sessions were designed for bike/assault bike/rower — only the Norwegian 4×4 was explicitly for running. Tabata on an assault bike ≠ Tabata running (you cannot modulate outdoor running intensity meaningfully in 20-second windows). Always read the ACTUAL template, not the summary email. (2) The PT's intensity prescription ("shift to Zone 2") was correct but required calibration against the user's actual aerobic threshold (~<YOUR_RESTING_HR_BPM> from Samsung AT/AnT model) — generic zone labels from a coach need to be translated to specific HR targets. (3) When a PT combines strength + cardio in one session (e.g., Monday upper body + intervals), flag the logistics: combined sessions are longer (55-60 min not 30 min), need fueling adjustments (extra carbs), and require architectural solutions (run FROM the gym, don't bike home and go back out). (4) A PT's nutrition advice is usually correct but generic — "eat protein after training" is right but doesn't address the user's specific gaps (dinner protein deficit, TMG underdosing, etc.). Keep the profile-specific recommendations from this skill; layer the PT's structural advice on top.
- Do NOT score AHEI alcohol component as "Strong/✅" for near-abstainers. The AHEI-2010 alcohol component gives the HIGHEST score (10/10) to MODERATE drinkers (0.5-2 drinks/day for men). Abstainers/non-drinkers score ~2.5/10 — NOT 10/10. Scoring a near-teetotaler as "Strong" on the alcohol component inflates the overall AHEI estimate by ~7.5 points. This is a factual error in the AHEI framework, not an opinion about drinking. When computing AHEI: abstainer = 2.5/10, moderate = 10/10, heavy = 0/10. Always include a note that the AHEI alcohol score reflects a population-level association and does NOT mean the user should start drinking — near-abstention is a lifestyle choice with negligible individual health impact
- Do NOT state a rule and then provide a default option that violates the rule. Example: "The One Rule: get 30-40g protein post-gym" with a default of Tunacado (21g) — the default doesn't meet the rule's own threshold. Before publishing any rule+default pair: verify the default satisfies the stated rule. If it doesn't, either lower the rule's floor to match the default (e.g., "20-40g") or change the default to a higher-protein option. This is a general consistency check that applies to any threshold-based recommendation with a named default option
- Do NOT overwrite a prior conclusion on a single weaker paper — surface conflicts explicitly
- Do NOT blend paper-derived and profile-derived recommendations without source attribution — every recommendation must cite its origin [PAPER/PRIOR/PROFILE/GENERAL]
- Do NOT present [GENERAL] knowledge as if it were [PAPER]-backed — general nutrition knowledge is the weakest source and must be flagged as such
- Do NOT omit source tags when synthesizing across multiple papers — the user needs to see which paper supports which recommendation

### Evolution Path

This skill is Layer 2 in a three-layer architecture:

- **Layer 1:** `<YOUR_HEALTH_DIR>/health-profile.md` — the data layer (bloods, supplements, fitness, interpretation rules). Continuously updated as new data arrives. This is a STRUCTURED COPY; the canonical raw source is `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`. Keep both in sync — see Step 2b.
- **Layer 2:** This skill — the research filter for health/longevity questions.
- **Layer 3:** Multi-agent orchestration for complex health questions. **Task shape determines the pattern** — see Layer 3 Decision Framework below.

#### Layer 3 Decision Framework — Debate vs Synthesis

Not all complex health questions need the same orchestration. The task shape determines the pattern:

**DEBATE (5-phase, 4 experts + validator)** — for contested decisions with real trade-offs:
- "Should I take rapamycin/fasting/nothing for inflammation?"
- "Critique this training plan — what could go wrong?"
- "Drop Zone 2 and add intervals given my HRV trend?"
- "Should I trust this Reddit protocol?"
- Pattern: 4 experts independently → mutual critique → sequential discussion with validator → final positions → synthesis
- Use: `deliberate` skill with health domain pack (`$HERMES_HOME/skills/deliberate/domains/health/` — the TOP-LEVEL deliberate copy; the `operations/deliberate` copy has no domain pack). This IS the ported health-coach — 4 personas + CLI validator, 5-phase protocol, eval-refined guardrails.

**SYNTHESIS (2-stage pipeline, 5 agents)** — for prioritization and system-building:
- "Draft a life operating system for my biomarkers"
- "What should I focus on across all my health data?"
- "Distill 600 lines of data into top 5 principles"
- Pattern: 4 domain experts in parallel (brief ~200 words each) → single synthesizer produces coherent output
- Why NOT debate: debate fragments the output into factions that need reconciling. An operating system needs one voice, not a treaty. The bottleneck is comprehension, not reasoning structure.
- Use: `deliberate` skill — run Phase 1 only (independent briefs) + Phase 5 (synthesis). Skip Phases 2-4 (critique, discussion, validator) unless the output reveals genuine disagreement that needs resolution.

**SINGLE-AGENT + PEER-REVIEW** — for narrow, single-domain questions:
- "What does this one paper mean for me?"
- "Should I increase my TMG dose?"
- Pattern: this skill (Layer 2) → peer-review for blind spots

The rule: **debate for decisions, synthesis for systems, single-agent for specifics.** When unsure, start with synthesis — it's faster and produces more coherent output. Escalate to debate only when genuine expert disagreement is expected.

### Data Architecture Principle: 3-Document Structure (EXECUTED 2026-06-30)

The health data architecture has been consolidated from 4 documents to 3 after this session's harmonization pass. The user explicitly said "Let's not overdocument." The final structure:

1. **`<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`** — **DATA ONLY.** Raw blood panels, body comp, sleep, skincare, factual intake logs (supplements taken, diet patterns observed). Strategy content has been stripped out and replaced with cross-references to the strategy doc.
2. **`<YOUR_HEALTH_DIR>/<YOUR_TRAINING_PLAN>.md`** — **STRATEGY + OPERATIONS.** Training program, nutrition strategy, supplement protocol, food framework (including restaurant menu reference with verified nutrition data), biomarker monitoring schedule, phased implementation plan. This doc absorbed the now-deleted `<YOUR_FOOD_GUIDE>.md`.
3. **`<YOUR_HEALTH_DIR>/<YOUR_NUTRITION_PLAN>.md`** — **FOOD-BIOMARKER REFERENCE.** Academic mapping of foods to biomarker targets, AHEI cross-check, compression list. Generated by this skill.

**`<YOUR_FOOD_GUIDE>.md` was DELETED** — its content (Tunacado tiers, eat-before-home architecture, carb periodization, restaurant menus, decision tree) was fully folded into `<YOUR_TRAINING_PLAN>.md` §3 + §3.5.

**Discipline rule:** When a new health document is about to be created, check whether its content belongs in one of the 3 existing docs. A 4th document is almost always overdocumentation. The user flagged this explicitly.

A `performance-nutrition` skill (same profile, athletic performance lens) and a `nutrient-tracking` skill (closed-loop intake logging + delta monitoring) are future possibilities. Build one skill at a time, let real gaps surface from usage.