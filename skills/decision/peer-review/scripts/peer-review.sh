#!/usr/bin/env bash
# peer-review.sh — Run a peer-review prompt via the best available CLI.
# Dumb pipe: sends a prompt to an external LLM and returns its stdout.
#
# CLI chain (harmonized across all deliberation skills):
#   1. command-code (primary)
#   2. agy (fallback)
#   3. mimo (fallback)
#   4. Exit 3 → signals the agent to run the peer as a native delegate_task subagent
#      (also the outcome when NO cli is installed — a missing CLI is not an error)
#
# Usage:
#   scripts/peer-review.sh "<prompt>"
#   echo "<prompt>" | scripts/peer-review.sh
#
# Override the workspace dir: PEER_REVIEW_WORKDIR=/path/to/repo peer-review.sh
#
# Exit codes: 0 success | 1 no prompt | 3 no usable CLI — none installed, or all failed
#             (either way: run the peer as a delegate_task subagent)

set -uo pipefail

# Harvest PATH additions from shell profiles (nvm/fnm/volta) in a disposable
# child shell: a profile that is noisy or fatal (unbound variable, exit, exec)
# must not terminate this script or suppress its no-CLI signal (exit 3).
# KEEP IN SYNC: grill-adversary.sh and loop/scripts/check.sh carry variants of this harvest block
# (no ~/.zprofile, no set +e/-e wrap) — if you change the approach, change all three.
set +e
for profile in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.zprofile ~/.profile; do
  [[ -f "$profile" ]] || continue
  harvested=$(bash -c 'set +u; source "$1" >/dev/null 2>&1; printf %s "$PATH"' bash "$profile" 2>/dev/null)
  # Adopt only additive harvests: non-empty, single-line, nothing dropped from
  # the inherited PATH, and something added.
  case "$harvested" in
    ""|"$PATH"|*$'\n'*) : ;;
    *)
      additive=1
      oldIFS=$IFS; IFS=:
      for entry in $PATH; do
        [ -n "$entry" ] || continue
        case ":$harvested:" in *":$entry:"*) : ;; *) additive=0 ;; esac
      done
      IFS=$oldIFS
      [ "$additive" = 1 ] && PATH="$harvested"
      ;;
  esac
done
set -e

# cd to the workspace so CLIs with cwd-scoped file access can see user files.
WORKDIR="${PEER_REVIEW_WORKDIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$WORKDIR" || { echo "Error: Failed to cd to '$WORKDIR'" >&2; exit 1; }

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then PROMPT=$(cat); fi
if [[ -z "$PROMPT" ]]; then
  echo "Usage: peer-review.sh \"<prompt>\" or pipe a prompt via stdin" >&2
  exit 1
fi

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT
printf '%s\n' "$PROMPT" > "$TMPFILE"

# `timeout` is GNU coreutils; stock macOS ships neither it nor coreutils' gtimeout
# alias, so every tier died with exit 127 before the CLI was even invoked — the
# chain then reported "all failed" on a machine where all three CLIs are installed
# (observed 2026-09-13, dogfooding the chain on macOS). Fall back to gtimeout,
# then to a perl alarm: perl is already this repo's documented macOS fallback
# engine (the leak gate uses it the same way), and the alarm survives exec.
run_timeout() {
    if command -v timeout >/dev/null 2>&1; then
        timeout "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$@"
    else
        perl -e 'alarm shift; exec @ARGV or exit 127' -- "$@"
    fi
}

# ── CLI routing (harmonized pattern across peer-review, grill, deliberate) ──

try_cli() {
    local cli="$1"; shift
    local prompt_file="$1"; shift

    case "$cli" in
        command-code)
            run_timeout 180 command-code -p "$(cat "$prompt_file")" --tools-all --skip-onboarding -t </dev/null 2>/dev/null
            ;;
        agy)
            run_timeout 180 agy -p "$(cat "$prompt_file")" --dangerously-skip-permissions --print-timeout 180s </dev/null 2>/dev/null
            ;;
        mimo)
            run_timeout 180 mimo run "$(cat "$prompt_file")" </dev/null 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# Try CLIs in priority order
# NOTE: set -e must be disabled during CLI calls — if a CLI returns non-zero
# (e.g., command-code after auto-update), set -e would abort the script before
# the fallback chain can try the next CLI. The entire fallback design depends
# on this.
set +e
for CLI in command-code agy mimo; do
    if ! command -v "$CLI" &>/dev/null; then
        continue
    fi

    OUTPUT=$(try_cli "$CLI" "$TMPFILE" 2>&1)
    EC=$?

    if [ $EC -eq 0 ] && [ -n "$OUTPUT" ]; then
        printf '%s\n' "$OUTPUT"
        exit 0
    fi
    echo "Warning: $CLI failed (exit $EC), trying next" >&2
done
set -e

# ── No usable CLI → signal the agent to run the peer as a subagent ────────
# A missing CLI is not an error: it carries the same instruction as "all failed".

INSTALLED=0
for CLI in command-code agy mimo; do
    command -v "$CLI" &>/dev/null && INSTALLED=$((INSTALLED + 1))
done

if [ "$INSTALLED" -eq 0 ]; then
    echo "No peer CLI installed (checked: command-code, agy, mimo). Use the native delegate_task subagent as the peer." >&2
else
    echo "All $INSTALLED installed peer CLI(s) failed. Use the native delegate_task subagent as the peer." >&2
fi
exit 3
