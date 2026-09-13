#!/usr/bin/env bash
# Grill adversary runner — routes through an external LLM CLI for model independence.
#
# CLI chain (harmonized across all deliberation skills):
#   1. command-code (primary)
#   2. agy (fallback)
#   3. mimo (fallback)
#   4. Returns "NO_CLI_FOUND" (exit 3) → fall back to delegate_task
#
# Usage: grill-adversary.sh "<prompt>"

set -uo pipefail

# Harvest PATH additions from shell profiles (mimo is only on PATH via
# ~/.bashrc — the Xiaomi installer does not symlink into /usr/local/bin) in a
# disposable child shell: a profile that is noisy or fatal (unbound variable,
# exit, exec) must not terminate this script or suppress NO_CLI_FOUND (exit 3).
# KEEP IN SYNC: peer-review.sh carries a variant of this harvest block (it also sources ~/.zprofile
# and wraps the loop in set +e/-e); loop/scripts/check.sh matches this one — change all three
# together if you change the approach.
for p in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.profile; do
  [[ -f "$p" ]] || continue
  harvested=$(bash -c 'set +u; source "$1" >/dev/null 2>&1; printf %s "$PATH"' bash "$p" 2>/dev/null)
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

PROMPT="${1:-}"
if [ -z "$PROMPT" ]; then
    PROMPT=$(cat)
fi
if [ -z "$PROMPT" ]; then
    echo "Usage: grill-adversary.sh \"<prompt>\" or pipe a prompt via stdin" >&2
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
# KEEP IN SYNC with peer-review.sh's run_timeout — same helper, same reasoning.
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
            run_timeout 180 command-code -p "$(cat "$prompt_file")" --skip-onboarding -t </dev/null 2>/dev/null
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
for CLI in command-code agy mimo; do
    if ! command -v "$CLI" &>/dev/null; then
        continue
    fi

    RESULT=$(try_cli "$CLI" "$TMPFILE")
    RC=$?

    if [ $RC -eq 0 ] && [ -n "$RESULT" ]; then
        echo "--- Adversary via $CLI ---"
        echo "$RESULT"
        exit 0
    fi
done

echo "NO_CLI_FOUND"
exit 3
