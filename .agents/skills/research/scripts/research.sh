#!/usr/bin/env bash
# research.sh — Thin wrapper around research.py for consistent skill invocation.
#
# Usage:
#   scripts/research.sh "[skill-dir]" "<any research.py args>"
#
# If $1 is an existing directory, it's used as the skill dir to derive
# the project root (passed from ${CLAUDE_SKILL_DIR} in SKILL.md).
#
# Exit codes: 0 success | 1 API error | 2 config error | 3 python not found

set -eo pipefail

# Source shell profiles for PATH additions
set +e
for profile in ~/.bashrc ~/.bash_profile ~/.zshrc ~/.zprofile ~/.profile; do
  # shellcheck disable=SC1090 # dynamic profile path by design
  [[ -f "$profile" ]] && source "$profile" 2>/dev/null
done
set -e

# Resolve project root
if [[ -n "${1:-}" && -d "$1" ]]; then
  SKILL_DIR="$(cd "$1" && pwd)"
  shift
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

SCRIPT="$SKILL_DIR/scripts/research.py"

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found in PATH" >&2
  exit 3
fi

exec python3 "$SCRIPT" "$@"
