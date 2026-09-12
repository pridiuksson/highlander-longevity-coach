---
name: eval-health
license: MIT
description: "Evaluate health-coach skill quality. Runs golden questions against health-coach, measures coverage/hallucinations/missed themes against concrete thresholds, analyzes phase-by-phase performance, persona differentiation, orchestration fidelity, and validator calibration. Produces a comprehensive eval report. Observer-only — never edits health-coach files."
allowed-tools:
  - Read
  - Grep
  - Glob
  - Agent
  - Write
argument-hint: "[run-path | latest]"
metadata:
  hermes:
    config:
      - key: health.health_dir
        description: "Root of your health data: device exports, SQLite DB, verified-data docs"
        default: "~/health"
        prompt: "Root of your health data: device exports, SQLite DB, verified-data docs"
---

# Eval Health

> **Config.** This skill reads its paths from `config.yaml`; the resolved values
> arrive in the `[Skill config]` block injected when this skill loads. In the
> commands below `$HEALTH_DIR` = `health.health_dir`.
> Never hardcode a path — a clone can live anywhere, and `~/health` is only a default.

Evaluate the health-coach skill by running golden questions and measuring output quality against concrete thresholds. **Observer-only** — you read, evaluate, and suggest. You never edit health-coach files.

## When to Use

- After persona prompt changes
- After SKILL.md orchestration changes
- After REFERENCE.md template changes
- After golden question additions or modifications
- Periodically to verify quality hasn't degraded
- When investigating why a specific phase underperformed
- When calibrating validator sensitivity

## Process

### Step 1: Identify the Run to Evaluate

If `$ARGUMENTS` specifies a run path (e.g., `health.health_dir/evals/run-001`), use that.

If `$ARGUMENTS` is `latest` or empty, find the latest run:
```bash
ls $HEALTH_DIR/evals/ | grep 'run-' | sort -V | tail -1
```

Verify the run contains `debate.json`. If only separate `phaseN.json` files exist (old format), tell the user: "This run uses the old multi-file format. Re-run `@health-coach` with the updated skill to generate a `debate.json`, then re-evaluate."

If no runs exist, tell the user: "No health-coach runs found. Run `@health-coach "question"` first."

### Step 2: Load Golden Questions

Read `.agents/skills/eval-health/golden-questions.json`. This contains predefined questions with expected themes at three tiers:

| Tier | Meaning | Coverage Threshold |
|------|---------|-------------------|
| `must_mention` | Critical themes — health-coach MUST address these | ≥80% coverage |
| `should_mention` | Important themes — health-coach SHOULD address these | ≥60% coverage |
| `nice_to_mention` | Bonus themes — nice if health-coach addresses these | No threshold |

### Step 3: Analyze the Run's Debate JSON

Read `debate.json` from the run directory. All phases are under `phases.phaseN`:
- `phases.phase1.responses` — Independent analysis (check each expert's response)
- `phases.phase1.word_counts` — Per-expert word counts
- `phases.phase2.critiques` — Structured critiques (check for DISAGREEMENTS)
- `phases.phase3.turns` — Discussion turns array
- `phases.phase3.turns[].validator.findings` — Validator findings per turn (each finding has `tag`, `claim`, `reason`). Evidence updates are NOT stored in `debate.json` — reconstruct them by chaining findings from prior turns: findings from turn N form the evidence updates injected into turn N+1's prompt. Turn 1 has no prior findings (empty updates).
- `phases.phase3.validator_summary` — Pre-computed counts: `ok_count`, `warn_count`, `fail_count`
- `phases.phase4.positions` — Final positions (each expert is `{position: "text", confidence: "LEVEL"}`)
- `phases.phase5` — Synthesis top-level fields: `consensus`, `differences`, `safety_check`, `evidence_level`
- `phases.phase5.synthesis` — Nested synthesis fields: `bottom_line`, `key_insight`, `the_answer`, `safety_considerations`, `caveats`

For each golden question's themes, check:
1. **Coverage**: Which themes appear in which phase and which persona?
2. **Hallucinations**: Use `phases.phase3.validator_summary` for pre-computed `warn_count` + `fail_count`. Cross-reference against `phases.phase3.turns[].validator.findings` for evidence quotes.
3. **Missed themes**: Which themes from must_mention/should_mention don't appear in any phase?
4. **Debate quality**: Did experts disagree? Did the validator catch issues?
5. **Phase analysis**: Did each phase achieve its goal? (see Phase Analysis template below)
6. **Persona differentiation**: Are Phase 1 responses meaningfully different? Did each persona express their adversarial stance and confidence calibration?
7. **Orchestration fidelity**: Did the skill run as designed? (expert count, turn count, field completeness, findings serialization)
8. **Validator calibration**: Is the validator appropriately sensitive? (0 flags on many claims = under-sensitive; high flag rate = over-sensitive)
9. **Evidence update tracking**: For each [WARN]/[FAIL] finding, did a later expert acknowledge it? (requires `evidence_updates` field in turns — pre-Phase-1 runs won't have this)

### Step 4: Calculate Metrics

**Coverage score** (per tier):
```
coverage = themes_found / total_themes_in_tier
```

**Hallucination count**:
```
hallucinations = phases.phase3.validator_summary.warn_count + phases.phase3.validator_summary.fail_count
```
For evidence details, extract from `phases.phase3.turns[].validator.findings` where `tag` is "WARN" or "FAIL".

**Missed themes**:
List all must_mention and should_mention themes not found in any phase.

**Debate quality score**:
- Experts disagreed (DISAGREEMENTS section in `phases.phase2.critiques`): +1
- Validator was active (≥1 finding in `phases.phase3.turns[].validator.findings`): +1
- Synthesis is substantive (≥50 words across `phases.phase5.synthesis.*` fields): +1
- Key insight present in `phases.phase5.synthesis.key_insight`: +1
Score: 0-4

**Phase analysis** (per phase):
- Phase 1: Count expert keys in `phases.phase1.responses`. FAIL if <4. (`word_counts` is a cross-check.)
- Phase 2: Check for DISAGREEMENTS sections in `phases.phase2.critiques`. FAIL if no disagreements found.
- Phase 3: Count turns in `phases.phase3.turns` array. FAIL if <8 (hard floor per SKILL.md). ⚠️ note if <8 but ≥4 — ran but violated the minimum turn constraint.
- Phase 4: Compare `phases.phase4.positions.*.position` text against Phase 1 responses. Note if positions evolved or stayed identical.
- Phase 5: Check all 9 required fields — 4 at top level (`consensus`, `differences`, `safety_check`, `evidence_level`) + 5 under `synthesis` (`bottom_line`, `key_insight`, `the_answer`, `safety_considerations`, `caveats`). FAIL if any missing. FAIL if synthesis could have been written from Phase 1 alone.

**Persona differentiation**:
- For each persona in Phase 1: identify themes unique to them (not raised by others).
- Check if each persona's stated adversarial stance (from their persona .md file) is expressed in their Phase 1 output.
- Flag if ≥3 personas converge on the same top-3 themes.

**Orchestration fidelity**:
- Compare actual expert counts, turn counts, and field counts against SKILL.md expectations.
- Note any dimension that deviates from expected.

**Validator calibration**:
- If warn_count == 0 AND fail_count == 0 AND total_claims > 5: flag as potentially under-sensitive.
- If warn_count + fail_count > total_claims * 0.5: flag as potentially over-sensitive.

**Findings serialization check** (verify change 1.4 worked):
- `total_findings` = sum of lengths of all `phases.phase3.turns[].validator.findings` arrays.
- `summary_total` = `validator_summary.ok_count + validator_summary.warn_count + validator_summary.fail_count`.
- If `total_findings != summary_total`: flag as ⚠️ — findings are truncated, serialization incomplete.

**Evidence update acknowledgment** (informational, requires `evidence_updates` field):
- For each [WARN] or [FAIL] finding in `phases.phase3.turns[].validator.findings`:
  1. Note the turn number and the claim.
  2. Check if any later turn's response (turns N+1 through 8) references or acknowledges that finding. Primarily check the **same speaker's next turn** (Round 2); secondarily check whether any other speaker references it.
  3. Track as: acknowledged / ignored / contradicted.
  4. **Acknowledgment requires one of**: (a) the speaker explicitly narrows or retracts the flagged claim, (b) they discuss the same topic with qualified language ("the evidence is mixed", "I should be more cautious"), or (c) they paraphrase or reference the validator's correction.
- `acknowledgment_rate` = acknowledged findings / total WARN+FAIL findings.
- Target: ≥50% (from Phase 1 success metrics).
- Evidence updates are not stored in `debate.json` — reconstruct them from the validator findings chain: the findings from turns 1 through N-1 were available as evidence updates when turn N's expert spoke. If `phases.phase3.turns` exists with validator findings, evidence update tracking is possible regardless of whether an explicit `evidence_updates` field is present.
- If there are zero validator findings across all turns, note: "No validator findings to track — validator may not have been active."

**Confidence language compliance** (informational):
- For each persona in Phase 3 turns, check for uncalibrated language patterns:
  - "proves" without RCT/meta-analysis citation
  - "likely explains" or "drives" for mechanistic reasoning without cited evidence
  - "the only thing that can" in any context
  - Unsupported causal chains (A → B → C) where a link lacks evidence and isn't labeled as hypothesis
- Count violations per persona. Flag persistent offenders in improvement suggestions.

### Step 5: Determine Pass/Fail

**PASS** if ALL of:
- ≥80% must_mention themes covered
- Hallucination count = 0 (no [WARN] or [FAIL] tags)
- ≤1 missed theme from must_mention tier
- Debate quality score ≥ 2
- Phase analysis: all 5 phases PASS
- Orchestration: no ⚠️ dimensions (all phases ran as designed)

**FAIL** if ANY of:
- <80% must_mention themes covered
- Hallucination count > 0
- >1 missed theme from must_mention tier
- Debate quality score < 2
- Phase analysis: any phase FAIL
- Orchestration: any ⚠️ dimension (e.g., only 2 of 4 experts, or 2 of 8 turns)

**Notes**:
- Persona differentiation, validator calibration, evidence update acknowledgment, and confidence language compliance are informational — they inform improvement suggestions but do not affect pass/fail.
- A PASS verdict that includes a ⚠️ validator calibration (0 flags on many claims) should note this as a concern in the verdict explanation.
- A PASS verdict with a low evidence update acknowledgment rate (<50%) should note this as a concern — the Evidence Updates feature (change 1.2) may need template adjustments.

### Step 6: Generate Eval Report

Write the report to the run directory as `eval-report.md`:

```markdown
# Eval Report — Run NNN

**Generated**: [date]
**Question evaluated**: [golden question text]
**Pass/Fail**: [PASS/FAIL]

## Coverage Report

### Must Mention (threshold: ≥80%)
| Theme | Found | Phase | Persona | Evidence |
|-------|-------|-------|---------|----------|
| {theme} | ✅/❌ | {phase} | {persona} | {quote or reference} |

Coverage: X/Y (Z%)

### Should Mention (threshold: ≥60%)
| Theme | Found | Phase | Persona | Evidence |
|-------|-------|-------|---------|----------|

Coverage: X/Y (Z%)

### Nice to Mention
| Theme | Found | Phase | Persona |
|-------|-------|-------|--------|

## Phase Analysis

Per-phase "did this phase achieve its goal?" check.

| Phase | Goal | Pass/Fail | Evidence |
|-------|------|-----------|----------|
| Phase 1 | 4 independent perspectives | ✅/❌ | {persona count from `phases.phase1.word_counts` keys, semantic divergence note} |
| Phase 2 | Substantive disagreements found | ✅/❌ | {disagreement count from `phases.phase2.critiques`, quality note} |
| Phase 3 | Genuine mind-changing across turns | ✅/❌ | {position drift between turns, turn count vs expected 8} |
| Phase 4 | Positions evolved from debate | ✅/❌ | {diff vs Phase 1 per persona from `phases.phase4.positions.*.position` — zero drift = debate had no effect} |
| Phase 5 | Synthesis > best single persona | ✅/❌ | {utility judgment, structural conformance — all 9 fields present?} |

Rules:
- Phase 1 FAIL if <4 expert responses in `phases.phase1.responses` (check `word_counts` keys)
- Phase 3 FAIL if turn count < 8 (hard floor per SKILL.md — "Minimum 8 turns required. Do NOT exit Phase 3 early.")
- Phase 5 FAIL if any required field is missing (4 top-level: `consensus`, `differences`, `safety_check`, `evidence_level`; 5 nested: `synthesis.bottom_line`, `synthesis.key_insight`, `synthesis.the_answer`, `synthesis.safety_considerations`, `synthesis.caveats`)
- Phase 5 FAIL if synthesis could have been written from Phase 1 alone (judge: does it reference specific debate moments?)

### Persona Differentiation

Check if Phase 1 responses are meaningfully different.

| Persona | Themes Unique to This Persona | Overlap with Others | In-Character? |
|---------|------------------------------|--------------------|--------------------|
| longevity_scientist | {themes only they raised} | {high/med/low} | ✅/❌ |
| dietitian | {themes only they raised} | {high/med/low} | ✅/❌ |
| sports_medicine | {themes only they raised} | {high/med/low} | ✅/❌ |
| pragmatist | {themes only they raised} | {high/med/low} | ✅/❌ |

Rules:
- "In-character" = did they express their stated adversarial stance? Check persona .md file for adversarial defaults, then verify presence in Phase 1 output.
- Flag if ≥3 personas converge on the same top-3 themes (convergence = weak differentiation).
- Note if any persona failed to produce the required output format (check REFERENCE.md Phase 1 template).

Per-persona guardrail checks (from targeted guardrails in Phase 1 changes):
- **Longevity Scientist**: Check Phase 1 output for evidence quality tags [STRONG]/[MODERATE]/[WEAK] on claims (required by Output Format §2). Flag if claims lack tags.
- **Dietitian**: Flag if "selenium" + "CYP" or "omega-3" + "CYP" appear together — these are NOT CYP substrates per their guardrail.
- **Sports Medicine**: Flag if "creatine" + "rhabdomyolysis" appear as co-risk-factors — creatine is NOT a recognized rhabdomyolysis risk factor per their guardrail.
- **Pragmatist**: Flag if causal narrative language ("X explains Y", "X likely causes Y") appears without cited study or "hypothesis" label — per their "never invent causal mechanisms" guardrail.

## Hallucination Report

| Tag | Count | Details |
|-----|-------|--------|
| [OK] | X | |
| [WARN] | X | {claims} |
| [FAIL] | X | {claims} |

Total hallucinations: X

Serialization: {total_findings} findings in arrays vs {summary_total} in summary — {MATCH/⚠️ MISMATCH}

Calibration: {ok_count} OK, {warn_count} WARN, {fail_count} FAIL across {total_claims} claims.
{If warn_count == 0 AND fail_count == 0 AND total_claims > 5: "⚠️ Zero flags on {total_claims} claims — validator may be under-sensitive. Review `phases.phase3.turns[].validator.findings` manually."}
{If warn_count + fail_count > total_claims * 0.5: "⚠️ High flag rate ({percentage}%) — validator may be over-sensitive or experts made many unsupported claims."}
{If total_findings != summary_total: "⚠️ Serialization mismatch: findings arrays contain {total_findings} entries but summary reports {summary_total}. Hallucination count uses validator_summary (trusted), but {difference} findings have no array evidence — verify manually."}

## Evidence Update Tracking

| Finding | Turn | Speaker | Tag | Acknowledged? | Evidence |
|---------|------|---------|-----|---------------|----------|
| {claim text} | {N} | {persona} | WARN/FAIL | ✅/❌/🔄 | {quote from later turn acknowledging it, or "Not acknowledged in any later turn"} |

Acknowledgment rate: X/Y (Z%)
Target: ≥50%

{If zero validator findings across all turns: "⚠️ No validator findings to track — validator may not have been active."}
{If rate < 50%: "⚠️ Low acknowledgment rate — the Evidence Updates feature may need template adjustments. Consider strengthening the acknowledgment instruction in the Phase 3 CRITICAL RULES."}

## Confidence Language

| Persona | Violations | Examples |
|---------|-----------|----------|
| longevity_scientist | X | {uncalibrated phrases found} |
| dietitian | X | {uncalibrated phrases found} |
| sports_medicine | X | {uncalibrated phrases found} |
| pragmatist | X | {uncalibrated phrases found} |

{If total violations == 0: "✅ All experts used calibrated language throughout Phase 3."}
{If any persona has ≥3 violations: "⚠️ {persona} has {N} confidence language violations — the Confidence Calibration section in their persona file may need strengthening."}

## Missed Themes

- {theme} — why it matters

## Debate Quality

| Metric | Score | Detail |
|--------|-------|--------|
| Experts disagreed | ✅/❌ | {evidence} |
| Validator active | ✅/❌ | {finding count} |
| Synthesis substantive | ✅/❌ | {word count} |
| Key insight present | ✅/❌ | {insight text} |

Quality score: X/4

## Orchestration Notes

Did the skill run as designed?

| Dimension | Expected | Actual | Status |
|-----------|----------|--------|--------|
| Experts in Phase 1 | 4 | {count from `phases.phase1.word_counts` keys} | ✅/⚠️ |
| Experts in Phase 2 | 4 | {count from `phases.phase2.critiques` keys} | ✅/⚠️ |
| Phase 3 turns | 8 (2 per expert) | {count from `phases.phase3.turns` array} | ✅/⚠️ |
| Findings serialization | summary counts = findings array total | {total_findings} findings vs {summary_total} summary | ✅/⚠️ |
| Validator findings present | Yes (findings arrays populated) | {total findings count} | ✅/⚠️ |
| Experts in Phase 4 | 4 | {count from `phases.phase4.positions` keys} | ✅/⚠️ |
| Phase 5 fields | 9 required (4 top-level + 5 synthesis) | {count present in `phases.phase5`} | ✅/⚠️ |

Rule: Any dimension with ⚠️ gets a note in improvement suggestions explaining what was expected vs what happened.

## Verdict

[PASS/FAIL] — {reason}

## Improvement Suggestions

1. {specific persona prompt tweak}
2. {template adjustment}
3. {orchestration change}
```

## Constraints

- **Observer-only.** Never edit health-coach files. Read, evaluate, suggest.
- **Evidence-based.** Every coverage claim must cite a specific phase file and quote.
- **Thresholds are binary.** ≥80% is PASS, <80% is FAIL. No rounding, no "close enough."
- **Actionable suggestions.** Each improvement suggestion must reference a specific file and what to change.
- **Single report.** All analysis goes into one eval-report.md. Do not create separate artifact files (persona-observations.md, template-observations.md, etc.) — the single report is the interface.
- **Calibration is informational.** Validator calibration notes inform suggestions but do not affect pass/fail. Do not fail a run because the validator "might" be under-sensitive — flag it and move on.
