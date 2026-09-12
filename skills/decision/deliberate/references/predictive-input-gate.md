# Predictive-Input Gate — Deliberate Phase-0 Check

Reference for deliberate runs that ask a predictive (not descriptive) question: "predict risk X", "what will happen to metric Y", "what is the cause of Z".

## Origin
Added 2026-08-30 after run-008's partial voiding (4-0 vote on nap-contaminated bedtime series + non-reproducible unscored-gap series; one sentence of user testimony — "bedtime has been 23:20-23:40 for a year" — falsified both). Extended 2026-09-11 (run-009 gate-block) when a predictive gastric-cancer-risk deliberation was invoked with 4 predictive inputs MISSING (family history, H. pylori, smoking, framework) and only one verifiable exposure present (smoked salmon ≤5x/wk, IARC Group 3, no threshold model).

## The gate principle (hard)
> The panel can only be as good as the series it votes on.

Before ANY Phase 1 dispatch on a predictive question, the parent must:

1. **List every load-bearing input series** — the ones the predictive hypothesis stands or falls on (not descriptive data; the predictive inputs specifically).
2. **Re-derive each independently** — grep/file-read/line-cite; never rely on recollection or a prior session summary.
3. **Anchor-check vs human testimony** — "does this match lived experience / profile / memory?" Testimony beats a buggy probe. A probe that reproduces (independent method) beats testimony.

If (1) shows MISSING predictive inputs: **DO NOT SPAWN EXPERTS**. Spawning 4 experts to invent a number is the run-008 failure mode reproduced. Halt at Phase 0, document the missing inputs, ask the user to supply them (or to confirm a non-quantified / targeted / lower-tier output), and produce a parent-derived synthesis with zero fabricated numbers.

## The 4 predictive inputs — gastric-cancer-risk example (run-009, verified 2026-09-11)
Verified independently this session via grep across `<YOUR_HEALTH_DIR>/<YOUR_BASELINE_DOC>.md`, `<YOUR_NUTRITION_PLAN>.md`, `restaurant-reference.md`, `samsung-data/*.md`, and user profile / memory / session notes:

| # | Predictive input | Data source expected | Verified state (run-009) | Evidence line / grep result |
|---|---|---|---|---|
| 1 | Family gastric-cancer history (first-degree; age; recurrence) | `<YOUR_BASELINE_DOC>.md` / user testimony | MISSING (0 hits) | `grep -ni family\|hered\|gastric.*cancer` → 0 hits |
| 2 | H. pylori status (serology / breath / clinical) | `<YOUR_BASELINE_DOC>.md` / lab results | MISSING (0 hits) | `grep -ni helicobacter\|h\.pylori\|h\. pylori` → 0 hits |
| 3 | Smoking / tobacco exposure (current/former/never; pack-years) | `<YOUR_BASELINE_DOC>.md` / user testimony | MISSING (tracking absent; alcohol L464 exists → selective tracking confirms absence is unverified) | `grep -ni smoke\|tobacco\|cigarette` → 0 hits (vs alcohol L464 present) |
| 4 | Predictive framework (GASTRIC / PLCO-style / epidemiology-only) | User specification / brief | MISSING (none specified, none applied) | None present; none requested |

The ONLY verifiable gastric-cancer-relevant exposure found (independent grep + line-cited):
- Smoked/cured salmon ≤5x/wk (`<YOUR_BASELINE_DOC>.md` L446 lunch + L455 dinner; `<YOUR_NUTRITION_PLAN>.md` L42/149 recommendation to rotate). IARC Group 3 "not classifiable" (Nordic smoked salmon) — NOT Group 1 (Chinese-style salted fish = Group 1). No dose-threshold model (`<YOUR_NUTRITION_PLAN>.md` L175: "IARC carcinogen dose-response for smoked fish at typical Nordic intake levels — no threshold data").

- Profile factors to check for LOW-RISK-but-NOT-predictive status: dietary pattern, alcohol intake, vegetable/berry intake, body composition, iron status, homocysteine, and the standard metabolic/renal/liver/lipid panels. Read the user's actual status from their health file — never assume or invent it.

## Parent probes (must be written into the brief before Phase 1)
For any predictive deliberation, the brief must contain at minimum:
- PROBE 1: No predictive framework applied — any percent-risk claim is invented; must be flagged.
- PROBE 2: Only verifiable exposure — describe it, cite lines, state whether a dose-threshold exists (if not: rotation only, no number).
- PROBE 3: Profile favors LOW / HIGH / NEUTRAL risk direction — but this is epidemiology, not a predictive model; must not become a fabricated percent.
- PROBE 4 (testimony anchor): User profile/testimony contains or lacks confirmation of the predictive inputs; absence of tracking ≠ absence of exposure; explicit testimony required.

## Corrections ledger (must be added to `debate.json` if evidence lands mid-deliberation)
Format: `"phases.pre_delib_corrections"` array, numbered (`CORR-N`), each entry: the claim corrected, the verification that invalidated it, and the conservative downgrade. Every correction must propagate to every later phase with an explicit `OVERRIDES` instruction.

## When to halt vs proceed
- **HALT** (Phase 0 only): predictive inputs MISSING and user has NOT confirmed a non-quantified/targeted/lower-tier output. Produce parent-derived synthesis; no expert spawn; `phase1_experts_spawned: false`; clarification pending.
- **PROCEED (targeted)**: user confirms "run targeted — single exposure, no percent-risk". Full 5-phase structure permitted, but expert prompts must include an explicit instruction: DO NOT invent a number; debate only the exposure rotation + what's missing + framework request.
- **PROCEED (full)**: user supplies all 4 predictive inputs + framework preference. Full Phase 1–5 with validator, corrections-ledger, and independent Phase 5 CLI synthesis.
- **PROCEED (honest-no-number)**: user explicitly instructs "run anyway — I accept no number". Same as targeted but explicitly documented.

## Validation after synthesis
Per the judging protocol (§5 / SKILL.md):
1. Did experts actually disagree? (If not → domain pack / question weak.)
2. Validator flags in target 3-10 range?
3. Synthesis survives data contact — every number traced to source line?
4. Better than single opinion?
5. Actionable recommendations?
Plus, for gate-blocked runs: verify `phase1_experts_spawned: false`, `judge_verdict` references the gate, synthesis contains zero fabricated numbers, `next_steps_for_user` names the 4 missing inputs concretely.
