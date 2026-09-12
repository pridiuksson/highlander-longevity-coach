---
name: grill
license: MIT
description: "Use when facing 'should I do/build/adopt X?' — a real decision with stakes. Null hypothesis = NO, adversary must prove YES. Adversarial CLI + delegate_task agents (~2min). For binary decisions, not exploration."
version: 1.0
---

# Grill — Adversarial Decision Analysis

Stress-test proposals through adversarial research. **Default answer is NO —
research must prove YES.**

Use this when the decision has real stakes — money, time, hard-to-reverse changes. If it's a
small call, use your own judgment. If you want a quick gut check, use peer-review.

## Self-Encapsulation

This skill owns its own script (`scripts/grill-adversary.sh`). No cross-skill imports. If peer-review or deliberate evolve their scripts, this skill is unaffected. Harmony through patterns, not shared code. Do not import or symlink scripts from other skills — copy the pattern.

## Scope

| Scope | Flag | Agents | When |
|-------|------|--------|------|
| **Standard** | *(default)* | Adversary + Builder + Pragmatist | Architecture decisions, tool adoption — the normal case |
| **Light** | `--light` | Adversary only (via CLI) | Quick kill-test on a single claim |
| **Deep** | `--deep` | + External Researcher | When external tools/frameworks are involved |

Default is standard because grill is only invoked for high-stakes decisions. If
the call is small enough for light, you probably don't need grill at all — use
your own judgment or peer-review.

Mechanical criteria:
- light = one tool, one claim to verify
- standard = multi-file or multi-claim
- deep = external framework or library involved

## Process

### Step 1: Frame

Read the proposal (file path → read it, text → use it). Extract:

- **Decision question**: one sentence ("Should we adopt X for Y?")
- **Null hypothesis**: default is NO
- **Kill condition**: what single finding ends this immediately?
- **Fact claims**: every verifiable assertion (file paths, counts, API names, versions)
- **External claims**: any claims about external tools, libraries, or services

**Challenge the framing first.** Is this even the right question? "Should we
adopt X?" might need to be "What problem are we actually solving?" If the
question itself is wrong, stop here and reframe.

**Steelman the proposal.** Before the Adversary attacks, articulate the
strongest version of the argument for adoption. The Adversary should respond to
the best case, not a strawman.

Present the kill condition: *"Kill condition: if X is true, I'll stop
immediately without running further agents."*

### Step 2: Probe

Fire agents. Adversary runs first (via CLI for model independence). Standard
and deep agents run via delegate_task.

**No-interrupt warning:** delegate_task runs inside the parent turn. If the
user sends a new message mid-grill, all active children are cancelled and
work is discarded. Do not start a standard/deep grill if you expect
interruption.

**Context checklist for every delegate_task subagent** (subagents start with
zero context — they know nothing):
- The proposal text or file path
- Project root (absolute path)
- Relevant source files to read (absolute paths)
- Test command (if applicable)
- What to ignore (out-of-scope areas)
- Required output format: `## Findings`, `## Simpler Alternative`,
  `## Confidence` headings so synthesis can weight them

Specify `toolsets` per persona:
- Builder: `["file", "terminal"]`
- Pragmatist: `["file", "terminal"]`
- External Researcher: `["web"]`

#### The Adversary (always — via CLI)

The core agent. Routed through an external LLM (command-code, mimo, or agy)
for genuine model independence — different blind spots than the head model.

Mission: Verify claims against the codebase, then argue against adoption. For
each idea: find the simplest alternative, estimate value retained. Identify the
3 strongest reasons to reject. Find underplayed risks. Rate the cost of undoing.

```bash
ADVERSARY_PROMPT="You are an adversarial reviewer. Null hypothesis is NO.
For every idea proposed, you must find the simplest alternative and estimate
what % of value it retains. Identify the 3 strongest reasons to reject.
Find underplayed risks and internal contradictions.

PROPOSAL:
<proposal summary>

FACT CLAIMS TO VERIFY:
<numbered list of verifiable assertions>

State the simplest alternative for each idea. Rate the cost of undoing each
recommendation (LOW/MEDIUM/HIGH). Be specific — cite file paths, line numbers,
and concrete risks."

RESULT=$($HERMES_HOME/skills/software-development/grill/scripts/grill-adversary.sh "$ADVERSARY_PROMPT")
```

If the script returns "NO_CLI_FOUND" (exit 3), fall back to delegate_task with
the same prompt. Label the output "Adversary (fallback)".

#### The Builder (standard/deep — via delegate_task)

Mission: Can we actually build this? Read the relevant source files. Trace code
paths. Realistic effort estimate (optimistic × 1.5-2.0). Hidden dependencies.
What existing codebase patterns can be reused? What's the 80% version?

#### The Pragmatist (standard/deep — via delegate_task)

Mission: Can we deploy and maintain this? What's the ACTUAL problem this solves
(not the solution)? Is it worth the cost — time, infrastructure, maintenance
tax, opportunity cost? If this were your money, would you fund it?

#### The External Researcher (deep only — via delegate_task)

The hallucination killer. Only spawned when the proposal references external
tools or frameworks.

Mission: Fetch the tool's repository, documentation, registry page. Verify
every external claim — does this feature exist? Is it maintained? Find known
issues, breaking changes. Report with confidence level.

If this agent cannot reach the external resource, mark ALL external claims as
"Unverified" and report what was attempted.

### Step 3: Synthesize

Main agent only — no spawning.

**Quality gate**: For each agent's output, check: does it contain file:line
citations or specific evidence? Is it substantive (>100 words)? If not, flag as
unreliable and weight it lower.

**Kill condition check**: Did any agent find the kill condition? If yes — stop.
Present findings. Do not proceed to verdicts.

Then process through three lenses:

**Contradictions**: Where do agents disagree? Where does the proposal contradict
itself?

**Simplicity audit**: For every recommendation, did the Adversary or Builder
propose a simpler alternative? What % value retained? Is the gap worth the
extra complexity?

**Verdicts**:

| Verdict | Means |
|---------|-------|
| **GO** | Verified valuable, no simpler alternative, feasible, no fatal risks |
| **CONDITIONAL-GO** | Valuable but needs conditions met first (list them) |
| **DOWNGRADE** | Simpler alternative retains ≥70% value — use that instead |
| **NO-GO** | Debunked facts, fatal risks, or not worth it |
| **DEFER** | Insufficient info — needs user input or more research |

### Step 4: Present

```
## Grill: {Title}
**Decision**: {GO / CONDITIONAL-GO / DOWNGRADE / NO-GO / DEFER}

### Per-Idea Verdict
| Idea | Verdict | Simpler Alternative | Key Risk |

### Fact Corrections
{what was wrong in the proposal}

### External Verification
{what the External Researcher confirmed or debunked}

### Unverified Claims
{treat as assumptions}
```

Offer to save to a plan document if the analysis is worth keeping.

## When to Use

```
Is the decision high-stakes or hard to reverse?
├── NO → Skip this skill, use your own judgment or peer-review
└── YES → Grill is the right tool
    ├── External tool/framework involved? → --deep
    ├── Multi-file or multi-claim? → standard (default)
    └── One claim to kill-test? → --light
```

## Pitfalls

- **Don't ask "How can X help?"** — Ask "Should we use X?" with null hypothesis = NO.
- **Don't skip the Adversary** — It's the core. Always invoke it, via CLI for independence.
- **Don't skip External Researcher for external tools** — It's the hallucination killer.
- **Don't trust AI consensus** — Multiple agents agreeing = shared bias. Weight by evidence quality.
- **Don't hide uncertainty** — Mark unverified claims explicitly. Separate facts from assumptions.
- **Don't forget simpler alternatives** — The Adversary must find them for every idea.
- **Verify the Adversary's negative file claims.** The CLI adversary (command-code/agy) reads only what's in its prompt — it cannot browse the filesystem or read linked reference files (`references/`, `scripts/`, `templates/`). When it says "X not found in SKILL" or "can't verify," that means it couldn't read the file, not that the content doesn't exist. Always check the full skill directory before accepting a negative claim. Observed (2026-06-29): adversary claimed the loop skill's champion-challenger pattern "NOT FOUND in SKILL.md" — it exists in the `loop` skill's reference files, not in this one. This is the same "fabricated file reads" failure mode documented in peer-review's pitfalls.
