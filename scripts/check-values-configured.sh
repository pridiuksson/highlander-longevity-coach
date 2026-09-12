#!/usr/bin/env bash
# check-values-configured.sh — the owner-side guard for the value layer.
#
# The shape layer is the merge gate and enforces itself everywhere. The value layer is local,
# opt-in configuration, and its failure mode is specific: a layer that is *supposed* to be
# configured but silently is not, producing a PASS that reads as identity coverage.
#
# Deliberately NOT strict about an absent overlay. `.pre-commit-config.yaml` is committed, so
# failing on absence would block every contributor for a condition they cannot fix — a
# contributor's own identity is not what this denylist protects. Strictness begins once the layer
# has been set up, which is what "configured" means here:
#
#   overlay present and parses            -> pass
#   overlay present but has <YOUR_>       -> FAIL: a setup that looks done and checks nothing
#   explicit path given but missing       -> FAIL: broken config, not an absent layer
#   no overlay anywhere                   -> pass, with the NOT-CONFIGURED notice
#
# Exit: 0 pass | 1 the value layer is misconfigured

set -uo pipefail

EXTRA="${LEAK_PATTERNS_EXTRA:-}"
DEFAULT_EXTRA="$HOME/.config/leak/patterns.tsv"
if [ -z "$EXTRA" ] && [ -f "$DEFAULT_EXTRA" ]; then EXTRA="$DEFAULT_EXTRA"; fi

if [ -z "$EXTRA" ]; then
  echo "value layer: NOT-CONFIGURED — shape patterns run alone, so the identity checks (your"
  echo "             name, your handle) are NOT applied. To set it up:"
  echo "               mkdir -p ~/.config/leak"
  echo "               cp scripts/leak-patterns.local.example.tsv ~/.config/leak/patterns.tsv"
  exit 0
fi

if [ ! -f "$EXTRA" ]; then
  echo "FAIL: LEAK_PATTERNS_EXTRA points at $EXTRA, which does not exist." >&2
  echo "      A configured-but-missing value layer is a silent hole: fix the path, or unset" >&2
  echo "      LEAK_PATTERNS_EXTRA to run the shape layer deliberately rather than accidentally." >&2
  exit 1
fi

# Three ways a layer can be present and useless, all of which look identical to a working one
# from the verdict summary alone: a line that does not parse, a regex that does not compile (grep
# errors and matches nothing), and a file with no entries at all.
_bad=""
while IFS=$'\t' read -r _pn _pe _px; do
  # Strip leading whitespace first: an indented comment is a comment for the counter, so it must be
  # one for the parser too, or a legitimately-formatted file fails as "no regex".
  _pn="${_pn#"${_pn%%[![:space:]]*}"}"
  case "$_pn" in ''|\#*) continue;; esac
  if [ -z "${_pe:-}" ]; then _bad="${_bad:+$_bad; }entry '$_pn' has no regex"; continue; fi
  if [ -n "${_px:-}" ]; then _bad="${_bad:+$_bad; }entry '$_pn' has too many fields (a stray tab?)"; continue; fi
  grep -qP -e "$_pe" /dev/null 2>/dev/null
  if [ "$?" -ge 2 ]; then _bad="${_bad:+$_bad; }entry '$_pn' has an invalid regex"; continue; fi
done < "$EXTRA"
if [ -n "$_bad" ]; then
  echo "FAIL: $EXTRA: $_bad." >&2
  echo "      Every entry must be NAME<TAB>REGEX with a regex that compiles. A line that does not" >&2
  echo "      parse, or a regex that does not compile, matches nothing — which is indistinguishable" >&2
  echo "      from a pattern that has no hits." >&2
  exit 1
fi

N=$(grep -v '^[[:space:]]*#' "$EXTRA" | grep -cv '^[[:space:]]*$' || true)
INERT=$(grep -v '^[[:space:]]*#' "$EXTRA" | grep -c '<YOUR_' || true)
if [ "${N:-0}" -eq 0 ]; then
  echo "FAIL: $EXTRA has no entries — it is configured, and it checks nothing." >&2
  exit 1
fi
if [ "${INERT:-0}" -gt 0 ]; then
  echo "FAIL: $INERT of ${N:-0} value pattern(s) in $EXTRA are still <YOUR_...> placeholders." >&2
  echo "      They match the literal placeholder text, so the identity checks they name are not" >&2
  echo "      running: the setup looks done and checks nothing. Fill them in." >&2
  exit 1
fi

echo "value layer: configured (${N:-0} pattern(s) applied from $EXTRA)"
exit 0
