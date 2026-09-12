# CLI Quirks — command-code and agy

Empirical findings from debugging the peer-review fallback chain (2026-06-13; updated 2026-07-18: all three CLIs re-verified, versions updated, mimo corrected — see install source note below).

## command-code (v0.52.1, verified 2026-07-18)

**Location:** `/usr/local/bin/command-code` (npm global under `$HERMES_HOME/node/lib`)

### File access = cwd scope

command-code restricts file access to its current working directory. There is no `--cwd` or `--workspace` flag. The `--add-dir <dir>` flag *extends* access beyond cwd but does not replace it. This means:

- If the script `cd`s to `$HERMES_HOME/`, the peer literally cannot read `$HOME/highlander-longevity-coach/` or any project files outside that tree.
- This was the root cause of the original peer-review bug: the old script did `cd "$SCRIPT_DIR/../../.."` which resolved to `$HERMES_HOME/` on Hermes (the path math was designed for a Claude Code project layout).
- **Fix:** `cd "$HOME"` by default, overridable via `PEER_REVIEW_WORKDIR`.

### Optimal flags for headless use

```
command-code -p "$PROMPT" --max-turns 30 --skip-onboarding -t </dev/null
```

| Flag | Purpose |
|------|---------|
| `-p` | Print mode (non-interactive, output response, exit) |
| `--max-turns 30` | Let peer read a few files without artificial truncation (default is 10) |
| `--skip-onboarding` | Skip taste onboarding (required for automated runs) |
| `-t` | Auto-trust the project (cwd) — skip permission prompt |
| `</dev/null` | Prevent stdin hang in non-interactive mode |

Exit code 8 = hit `--max-turns` cap. The partial response was still printed — treat as success.

### Timeout causes

The real timeout cause is NOT the flags — it's slow LLM turns when the peer spends turns hunting for files it can't see (because of wrong cwd). Fixing cwd eliminates most timeouts. Remaining timeouts are from prompts >200 words or auto-update stalls.

### Hallucination under workspace restriction

When command-code can't access files but is asked to review them (via path reference in the prompt), it may **fabricate reading them** — inventing plausible function names, file structures, and "verified" claims. This is the most dangerous failure mode: authoritative-sounding output that is entirely invented. The peer-review SKILL.md's push-back pattern (verify claims against evidence) is specifically designed to catch this.

### Auto-update behavior

command-code auto-updates on first run after a version bump. This consumes the entire timeout. If you see "Updated X.Y.Z → X.Y.W" in output followed by termination, just retry — the update is done.

### Auto-update → empty output → non-zero exit (critical fallback bug)

**Observed 2026-07-03:** After an auto-update from 0.40.16 → 0.41.1, command-code printed "Updated 0.40.16 → 0.41.1" to stdout, then exited with code 0 but **empty OUTPUT** (the update message was on stderr, stdout was empty). The peer-review script checked `[ -n "$OUTPUT" ]` and correctly fell through. However, in a separate run, command-code exited non-zero (code 1) after the update with empty output. 

The critical issue: the script had `set -e` active during the CLI loop. `OUTPUT=$(try_cli ...)` captured the exit code into `EC`, but `set -e` caused the script to abort at the `try_cli` call itself before reaching the `EC=$?` check — the fallback chain was dead code. **Fix applied:** `set +e` before the loop, `set -e` after. Without this, if command-code fails, the script dies instead of trying agy/mimo.

## mimo (Xiaomi MiMoCode, v0.1.6 — installed 2026-07-18)

**Location:** `$HOME/.mimocode/bin/mimo` (installed via `curl -fsSL https://mimo.xiaomi.com/install | bash`). The installer appends `~/.mimocode/bin` to PATH in `~/.bashrc`.

CRITICAL — do not confuse with `mimocode` on npm (`npm i -g mimocode`). That is an unrelated opencode/Bun fork (v0.38.9) that is interactive-only — no `run` subcommand, no headless mode. The Xiaomi mimo CLI is distributed only from `mimo.xiaomi.com`. If `mimo --help` shows `mimo run [message..]` as a subcommand, you have the right binary. If it shows only `chat`, you have the wrong one — uninstall it and run the curl installer.

### Invocation — `run` subcommand, positional prompt

```bash
mimo run "<prompt>" </dev/null
```

The prompt is positional after `run`. Do NOT use `mimo -p` — that flag does not exist on this CLI. Verified end-to-end through the peer-review script on 2026-07-18.

### Output format

Prepends a single header line: `> build · <model-name>`. Non-empty content follows. This is the only CLI in the chain that prepends a prefix line; the peer-review script passes output through unchanged (the prefix is harmless in the agent's read).

### When to use

Tier 3 fallback — provides model diversity when command-code and agy are rate-limited or timing out. Slower than command-code but a genuinely different model perspective.

### PATH in non-interactive shells

The installer only modifies `~/.bashrc`, not `/etc/profile` or `/usr/local/bin`. Non-interactive shells won't find `mimo` unless they source a profile first. The peer-review script already sources `~/.bashrc`/`~/.profile` in a loop (see lines 21-25), so mimo resolves correctly inside that script. If you build new scripts that call mimo directly, source profiles or prepend `~/.mimocode/bin` to PATH explicitly.

### Upgrade

`mimo upgrade` — built-in self-update subcommand. Run periodically (Xiaomi ships frequent releases).

## agy (v1.1.4, Antigravity CLI — updated 2026-07-18 via `agy update`)

**Location:** `~/.local/bin/agy` (installed separately, already on PATH)

### Headless mode

```
agy -p "$PROMPT" --dangerously-skip-permissions --print-timeout 300s </dev/null
```

| Flag | Purpose |
|------|---------|
| `-p` / `--print` | Non-interactive: run prompt, print response, exit |
| `--dangerously-skip-permissions` | Auto-approve all tool use for automation |
| `--print-timeout 300s` | Timeout for print mode (default 5m) |
| `--add-dir <dir>` | Extend workspace file access beyond cwd |
| `</dev/null` | Prevent stdin hang in non-interactive mode |

### Output format

Clean stdout — no prefix lines to strip (unlike the old mimo CLI which prepended `> build · model-name`).

### Default model

Gemini 3.5 Flash (High) — good enough for peer reviews. No `--model` flag needed. To list alternatives: `agy models` (Claude Sonnet 4.6, Claude Opus 4.6, Gemini 3.1 Pro, GPT-OSS 120B, etc.).

### Hallucination of plausible-sounding technical explanations

Same danger as command-code: when agy can't verify a claim, it may fabricate a technically coherent explanation built on a false premise. Observed (2026-06-24): when asked about prompt cache differences between mem0 and Honcho, agy produced a detailed "Technical Cache Invalidation Mechanism" diagram showing how system-prompt injection breaks hierarchical caching — the mechanism was real in isolation, but the premise (that mem0 injects into system prompt) was entirely fabricated. Both providers inject into the user message via the same code path (`conversation_loop.py` line 723). The fabrication was caught only because the user questioned it and the agent read the actual source code. Treat any agy output that explains "how X works internally" as unverified until checked against source.

### File access

Operates on current working directory, same as command-code. Use `--add-dir` to extend access. The peer-review script `cd`s to `$WORKDIR` before calling agy, so file references in the prompt should resolve.

### Subcommands

- `agy models` — list available models
- `agy changelog` — release notes
- `agy plugin` — manage plugins

## Fallback chain design rationale

Tier 1 (command-code) is preferred because:
- Faster (~2s vs agy's ~5-10s)
- Already authenticated, no bootstrap overhead
- More mature tool (v0.37.2)

Tier 2 (agy) provides genuine model diversity — Gemini 3.5 Flash (High), a different model from a different provider (Google). Different failure modes from command-code. Good output quality.

Tier 3 (mimo, Xiaomi MiMoCode v0.1.6) is a third model option when both command-code and agy are unavailable. Different invocation pattern (positional args via `mimo run`, not `-p`). Verified working end-to-end through the peer-review script on 2026-07-18. Different provider again (Xiaomi) — genuine model diversity.

Tier 4 (native subagent via delegate_task) uses the same model as the calling agent (glm-5.2). It's the weakest tier for catching model-specific blind spots, but provides:
- Fresh context window (no context pollution from the main conversation)
- Different system prompt (reviewer framing)
- Web search capability if the question benefits from verification

The honest assessment from testing: "no review > fake review." Tier 3 is insurance against total CLI outage, not a primary review path.
