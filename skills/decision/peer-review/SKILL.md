---
name: peer-review
license: MIT
description: "Use BEFORE acting on any unverified assumption or guess. Quick second opinion from a different LLM via CLI (~15s). Catches blind spots, prevents confident errors. DEFAULT reflex for any uncertainty."
version: 2.3.0
author: ported from oracle
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [review, second-opinion, peer, sanity-check, command-code, agy, mimo]
---

# Peer-Review — Quick AI Gut Check

Bounce an idea off a different LLM. Quick sanity check, not deep adversarial analysis.

## Do this

**Before framing the prompt: fact-check what you can verify yourself.** The most effective peer reviews are narrowly scoped to genuine judgment calls, not things you could check with a terminal or file read. Audit the document/decision against source code, config files, or actual CLI output FIRST. Resolve every verifiable claim on your own. Then frame the peer prompt around ONLY what remains genuinely uncertain — design trade-offs, human-factors judgments, or questions where no source-of-truth exists. This makes the peer's limited context count.

Frame the user's request as a prompt. The act of writing the prompt forces you to articulate what you're uncertain about — that's where the value is.

The peer runs from `$HOME` and has file access to everything under it (including project repos like `~/highlander-longevity-coach`). To scope the peer to a specific repo, set `PEER_REVIEW_WORKDIR=/path/to/repo` before calling the script. Reference files by absolute path when helpful.

```bash
${HERMES_SKILL_DIR}/scripts/peer-review.sh "your prompt here"
```

Use the **terminal** tool to run the script. Set a **5-minute timeout** (300 seconds).

### Fallback chain (automatic in the script; tier 3 is yours to run)

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success — a CLI returned a response | Read stdout, proceed to evaluation |
| 1 | No prompt provided OR script error | Usage error: fix and retry. If a prompt WAS provided, check for script bugs (e.g., a `set -e` regression killing the fallback loop). |
| 3 | **No peer CLI available** — none installed, or all installed ones failed | **Use the native subagent fallback** (below). This is the expected path on a fresh box. |

There is no exit 2. **A missing CLI is not an error — it is the signal to delegate.** The chain is
`command-code → agy → mimo → exit 3`, and "none of them is installed" lands in exactly the same place as
"all of them failed", because the correct response is identical: run the peer as a subagent.

### Tier 3: Native subagent fallback

If the script exits **3** — which includes the case where no CLI is installed at all — spawn a subagent
as the peer:

```
delegate_task(
  goal="You are a peer reviewer. Give a quick, honest second opinion on this question. Do not rubber-stamp — flag blind spots and simpler alternatives. Keep it under 200 words.\n\nQUESTION:\n<paste your prompt here>",
  toolsets=["web"]
)
```

The subagent can read files and search the web if the question benefits from verification.

**Be honest about which tier you are actually in.** With a CLI installed, the subagent runs on a different
model from command-code/agy, so it is a genuine second opinion. With **no** CLI installed it runs on
Hermes's own model — that is a second *context*, not a second *model*: good at catching what you
overlooked, weaker at catching assumptions you both share. Still worth running (a second context beats no
review), but install at least one CLI when the decision is consequential enough to want real independence.

### After the peer replies

Report the peer's **main** insight in your own words. Then critically evaluate — don't rubber-stamp.

**When the peer agrees with your approach** (the most dangerous outcome): push back with "What's one specific way this could fail in production?" before accepting. Positive reviews need active stress-testing, not passive acceptance. Agreement without probing is sycophancy in both directions.

**Push back when the peer makes claims that don't hold up.** A confident-sounding review can be worse than no review if it's wrong. Before acting on the peer's findings:
1. Check each claim against evidence you already have (source code, docs, actual behavior)
2. If a claim contradicts your verified knowledge, challenge it with the specific mechanism or fact that disproves it
3. Send the challenge as a follow-up round — the peer may correct itself

This pattern (peer claims → you push back with evidence → peer revises) catches false positives that would otherwise lead you to "fix" things that weren't broken. The most dangerous review is one that sounds authoritative but is wrong — it takes active push-back to filter these out.

### Follow-up rounds

Run the script again with a follow-up prompt; up to **3** short rounds.

**Typical patterns:**
- **Push-back pattern (most valuable):** Round 1 → peer makes claims → you challenge the weakest ones with evidence → Round 2 → peer revises or confirms → act on what survived scrutiny.
- **Fix-confirm pattern:** Round 1 → get feedback → fix issues → Round 2 → confirm fixes land → stop.

Two rounds is usually enough. Only go to 3 if the second round surfaces new issues.

**Separated review pattern (concerns vs solutions).** When reviewing a document that pairs concerns with proposed solutions, do NOT review it as one blob. Run two short reviews: (1) **concerns only** — "are these the right concerns; what's missing or overweighted?"; (2) **concerns + solutions** — "will these close the concerns; which solution is weakest or overengineered for the actual scale?" Separation prevents solution plausibility from laundering concern quality — a well-argued solution list makes wrong concerns feel validated. Validated 2026-09-11 (multi-profile iteration): the concerns-only pass added 2 missing concerns (version skew, credential surface); the solutions pass surfaced an overengineering call (patch-file overhead at 4-profile scale) that the combined view had buried.

## CLI behavior reference

For command-code and agy CLI quirks (flags, file access scope, output format, timeout causes), see `references/cli-quirks.md`.

## Pitfalls

- **`set -e` kills the fallback chain (FIXED 2026-07-03).** The script used `set -e` during the CLI loop. If command-code returned non-zero (e.g., after an auto-update), `set -e` aborted the script before it could try agy or mimo — making the entire fallback chain dead code and causing the script to exit 1 instead of 3. Fixed by wrapping the loop in `set +e` / `set -e`. If the script exits unexpectedly with code 1 instead of falling through to exit 3, check for this regression.
- **Fabricated file reads (most dangerous).** When the peer can't access a file (wrong cwd, outside workspace scope), it may fabricate reading it — inventing plausible function names and "verified" claims. This is worse than no review. Always verify file-based claims against actual source. This was observed in production: command-code invented `_HERMES_PROVIDER_ENV_BLOCKLIST` and `env_passthrough.py` that don't exist anywhere on the machine.
- **Long prompts timeout.** Prompts over ~200 words often timeout at 300s. Keep prompts under 100 words — state the question, the decision point, and the constraint. Detail belongs in referenced files, not in the prompt text. If the peer times out, shorten and retry immediately.
- **Self-update stalls.** `command-code` auto-updates on first run after a version bump, which consumes the entire timeout. If you see "Updated X.Y.Z → X.Y.W" in output followed by termination, just retry — the update is done. See `references/cli-quirks.md` for the auto-update → non-zero exit pattern.
- **Empty responses.** A CLI can exit 0 with empty stdout (no output at all). The script treats this as failure and falls through to the next tier. If all tiers produce empty output, the prompt likely confused the model or triggered a safety filter. Retry with a shorter, more specific prompt.
- **File access scope.** Both CLIs scope file access to their working directory (`$HOME` by default). If the peer claims it can't read a file, check that the path is under `$HOME` or set `PEER_REVIEW_WORKDIR` to the right directory.
- **mimo install pitfall (resolved 2026-07-18).** The `mimo` CLI must be installed from `mimo.xiaomi.com` (`curl -fsSL https://mimo.xiaomi.com/install | bash`), NOT from npm. `npm i -g mimocode` installs an unrelated opencode fork that is interactive-only and breaks the chain — it rejects `mimo run "..."` with exit 0, which would silently inject error text as the peer's response. The Xiaomi installer only modifies `~/.bashrc` (not `/usr/local/bin` or `/etc/profile`), so non-interactive shells need the profile-sourcing preamble to find it. See `references/cli-quirks.md` for full mimo invocation details.
- **`timeout` is GNU coreutils — absent on stock macOS (FIXED 2026-09-13).** Every tier invoked `timeout 180 <cli>`; on macOS the missing binary itself exits 127, so all three installed CLIs "failed" with the identical code and the chain reported exit 3 despite nothing being wrong with the CLIs. `run_timeout` now falls back to `gtimeout`, then to a perl alarm. Symptom signature: identical failure codes across unrelated CLIs means the shared invocation wrapper is broken, not the CLIs. See `references/cli-quirks.md`.
- **Editing a `.sh` script can silently strip the execute bit.** A prior session rewrote `grill-adversary.sh` (the sibling skill's adversary script) and it landed as mode 600 — unreadable as a script, every invocation failed with "Permission denied" looking like a broken skill. If a script suddenly stops working after any edit, check `ls -la` for mode before debugging the content. Correct mode for these scripts is 711 (matching siblings).

## Maintaining the CLI chain

When updating, installing, or debugging any CLI in the fallback chain (command-code, agy, mimo), the goal is not just "is the binary present" but "does each tier actually fire when the higher-priority tier is unavailable." The script's `command -v` check only confirms presence — it does not confirm the CLI returns usable output.

**Before installing a CLI you think is missing, check existing skills first.** The `claude-code` skill (lines 865-962) already documents the authoritative mimo install path (`mimo.xiaomi.com`, NOT npm), complete with invocation patterns, model list, and config locations. Running `npm i -g mimocode` without checking cost a full round-trip in the 2026-07-18 session. This applies to any CLI a skill references — the install procedure is often already documented in a skill you haven't loaded.

**Verification pattern — force each tier in isolation.** A version check (`mimo --version`) only proves the binary runs. To prove the fallback chain actually fires through a specific tier, temporarily hide the higher-priority CLIs and run the real script:

```bash
sudo mv /usr/local/bin/command-code /tmp/cc.bak
sudo mv ~/.local/bin/agy /tmp/agy.bak
export PATH="$HOME/.mimocode/bin:$PATH"   # if mimo (only on ~/.bashrc PATH)
${HERMES_SKILL_DIR}/scripts/peer-review.sh "Reply with exactly: TIER_OK"   # no `timeout 60` wrapper — timeout is GNU coreutils, absent on stock macOS; the script bounds each tier itself and your tool-level timeout bounds the call
sudo mv /tmp/cc.bak /usr/local/bin/command-code
sudo mv /tmp/agy.bak ~/.local/bin/agy
```

If the response is the expected marker, that tier fires end-to-end through the actual script (profile sourcing, `try_cli` case, output capture, exit code). This caught the grill-adversary.sh permission bug — the script existed and `command -v` passed, but it was mode 600 and died at exec. Run this for each tier after any install/upgrade.

**Smoke-test prompt.** Use a trivial deterministic prompt ("What is 17 × 23?") as the end-to-end check — a wrong or empty answer means the chain is broken regardless of where. Avoid open-ended prompts for smoke tests; you need to recognize a correct answer instantly.

## Self-Encapsulation

This skill owns its own script (`scripts/peer-review.sh`). No cross-skill imports. If grill or deliberate evolve their scripts, this skill is unaffected. Harmony through patterns, not shared code. Do not import or symlink scripts from other skills — copy the pattern.

## When

This skill owns its own script (`scripts/peer-review.sh`). No cross-skill imports. If grill or deliberate evolve their scripts, this skill is unaffected. Harmony through patterns, not shared code. Do not import or symlink scripts from other skills — copy the pattern.

**Default reflex: when in doubt, peer-review it.** The threshold isn't "is this important enough to check?" — it's "am I about to act on an unverified assumption?" If yes, spend 15 seconds.

Specific triggers:
- Before planning — sanity check an approach
- During implementation — rubber-duck when stuck
- Before committing to a design — second opinion on trade-offs
- Before committing to a technology or architecture choice
- When reviewing skill or process changes
- **Before building or porting skills** — peer-review each candidate skill separately before doing the work.
- **Before implementing architecture-level changes (multi-profile isolation, skills derivation, data restructure)** — produce a `Knowledge/Plans/<topic>-research.md` document FIRST (design-first discipline, validated 2026-09-10 session). The multi-profile session did NOT build; it produced a design document with 3 parallel peer-reviews (R1 manifest audit, R2 HEALTH restructure, R4 divergence tracking) before any file was moved. Only after synthesis did real gaps surface: missing reconciliation mechanism (R4), premature restructure sequence (R2), contradiction between self-encapsulation and divergence tracking (R4). A design doc with peer-reviewed synthesis is the gate — build nothing until that synthesis exists and is verified against deliverable files.
- **For complex plans (architecture, multi-skill design, system design)** — run peer-review AND grill in parallel. They catch different things: peer-review catches architecture/UX issues, grill catches value/ROI issues. **Reflect on each separately before revising.** When both identify the same problem from different angles, it's real. When they diverge, the disagreement itself reveals a blind spot. This composition pattern was validated across multiple design iterations in a single session and consistently produced sharper thinking than either alone.
- **After building or porting skills** — peer-review each delivered skill separately. The "before" pass catches design issues; the "after" pass catches implementation bugs (broken scripts, contradictions, missing steps). This session: the "after" pass caught a broken adversary script (5 bugs), over-stuffed skill description, and methodology stitched into a tool reference. Every reviewed skill needed iteration. The double-pass pattern (review before + review after) has a 100% hit rate across 4 skills tested.

## Multi-document audit pattern (for reference documents derived from analysis)

When deliberation output, research findings, or expert analysis gets written to persistent reference documents (markdown files, knowledge base entries), those documents inherit a false authority — errors surrounded by correct information look credible. A multi-document audit catches cross-document contradictions and factual errors that single-pass review misses.

**When to use:** After writing 2+ reference documents from the same analytical session (deliberation, research, multi-expert analysis). Especially critical for health, financial, or legal documents where errors can cause harm.

**Technique — external-facts injection:**

The key innovation: give each reviewer facts NOT in the document being reviewed. This forces cross-referencing against ground truth the document author didn't have or ignored.

1. Spawn one subagent per document (parallel). Each gets:
   - The document to review (via read_file path)
   - 5-7 key facts NOT in the document (user's actual situation, source deliberation IDs, constraints, corrections from the live conversation)
   - Instruction to tag findings: 🔴 DANGEROUS / 🟡 MISLEADING / 🔬 FACTUAL ERROR / ⚠️ CONTRADICTION / 💡 MISSING
2. Verify the highest-severity findings yourself before patching
3. Patch all documents, then re-verify with a second round

**Validated results (June 2026, health documents):** 27 errors found across 3 documents from a single audit round. The most critical: a document recommended iron supplementation at a threshold that contradicted its own source deliberation's 4/4 expert consensus (NO supplement). The error existed for days because the document cited the wrong deliberation ID. External-facts injection (providing the correct deliberation ID and consensus) is what caught it.

**Verify the auditor (July 2026):** An audit document inherits the same false authority it's supposed to cut through. In a sports-science audit merge, 2 of the audit's 5 "factual error" findings were themselves factually wrong — the auditor misidentified a Cochrane review (claiming CD010405 was a heart-failure review; it's actually a CVD primary-prevention review) and fabricated a study-design claim (asserting Helgerud 2007's comparator was MICT, not LSD; LSD was a real study arm). Had these "corrections" been merged blindly, the document would have been made *worse*. **Rule: before merging any audit finding tagged as a factual error, independently verify the auditor's claim against the primary source — not just the document's claim.** Factual-error findings are the highest-risk to act on because they come packaged as authoritative corrections, making disagreement feel like defiance. Check anyway. The auditor is a document too.

**Why this works when self-review doesn't:** The document author (you, in a previous turn or session) is anchored on their own reasoning path. An independent reviewer with different context sees contradictions you're blind to. This is the same principle as the mem0-claims-verification skill, applied to documents instead of memory facts.

## Clean-context subagent testing (post-build validation)

After peer-review and bug fixes, validate **discoverability and usability** by spawning 1-2 subagents with clean context (no conversation history, no knowledge of the skill). Give them a realistic user query and see if they can:

1. Find and load the skill on their own (`skill_view(name='...')`)
2. Follow the instructions without guessing
3. Apply the thinking framework correctly
4. Produce good output

**Pattern:** Run 2 tests in parallel via `delegate_task(tasks=[...])`. Each subagent gets a different query type (e.g. one route query, one arrive-by planning). Report back: did they find it? was it clear? what friction did they hit?

**Why this matters:** Peer-review catches code bugs and design issues from the *builder's* perspective. Subagent testing catches documentation gaps that only surface when someone *without context* tries to follow the skill. In testing the `sl-transit` skill (Jun 2026), both subagents successfully used the skill but independently flagged the same two gaps: no guidance on arrival buffer sizing, and unclear rules for when to check disruptions. Both were real issues the builder couldn't see because they already knew the intended behavior.

**What to fix from subagent feedback:** Friction points where multiple agents independently stumble are real documentation gaps. Single-agent confusion may be a fluke. Fix the patterns, not the outliers.

---

## Overlap note

This skill's "Multi-document audit pattern" section and the `mem0-claims-verification` skill both use parallel subagents with external-facts injection to catch errors. They're complementary, not duplicative: peer-review audits reference documents; mem0-claims-verification audits stored memory facts. If consolidating, merge the shared methodology (parallel subagents, external-facts injection, severity tagging) into peer-review and have mem0-claims-verification reference it.
