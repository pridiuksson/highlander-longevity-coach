#!/usr/bin/env bash
# regression suite for reality_check.py — run before shipping any change
# usage: bash regression_suite.sh
#
# Runs against SEEDED COPIES in mktemp -d, never live files (the source engine's
# suite learned that lesson the hard way: an in-place rewrite once stripped the
# trailing newline of the user's live MEMORY.md on every run). Cases assert the
# enumerator's DETERMINISTIC output — parses, verdicts, exit codes — on synthetic
# fixtures, never a live verdict: a real change in the user's training SHOULD
# read as drift, and the suite must not call that a regression.
set -u
SCRIPT="$(cd "$(dirname "$0")" && pwd)/reality_check.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
PASS=0; TOTAL=0

# A source that emits a fresh, controllable signature set.
make_source() { # $1 = dir, $2 = python expr for the dict
  mkdir -p "$1"
  printf '#!/usr/bin/env python3\nimport json, datetime\nprint(json.dumps(%s))\n' "$2" > "$1/s.py"
}

run_case() { # name expect_rc needle absent memory_text source_expr
  local name="$1" expect_rc="$2" needle="$3" absent="$4" mem="$5" src="$6"
  TOTAL=$((TOTAL+1))
  local dir="$TMP/case_$TOTAL"
  mkdir -p "$dir/memories"
  printf '%s\n' "$mem" > "$dir/memories/MEMORY.md"
  make_source "$dir/sources" "$src"
  OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1)
  RC=$?
  OK=1
  [ "$RC" = "$expect_rc" ] || OK=0
  if [ -n "$needle" ] && ! echo "$OUT" | grep -qF "$needle"; then OK=0; fi
  if [ -n "$absent" ] && echo "$OUT" | grep -qF "$absent"; then OK=0; fi
  if [ "$OK" = 1 ]; then echo "ok   $name"; PASS=$((PASS+1)); else
    echo "FAIL $name (rc=$RC want=$expect_rc)"; echo "$OUT" | head -4; fi
}

FRESH="datetime.datetime.now(datetime.timezone.utc).isoformat()"

# --- exit contract ---
run_case "pending-review is exit 0 and never says CONGRUENT" 0 "PENDING-REVIEW" "CONGRUENT" \
  "Runs 2/wk." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "drift exits 1" 1 "DRIFT" "" \
  "Runs 2/wk." "{'runs_per_week': 6.0, 'data_end': $FRESH, 'coverage_days': 28}"

# no-sources case: dir with no scripts
TOTAL=$((TOTAL+1))
dir="$TMP/case_nosources"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "2" ] && echo "$OUT" | grep -qF "NO_DATA"; then echo "ok   no sources exits 2"; PASS=$((PASS+1)); else echo "FAIL no sources (rc=$RC)"; echo "$OUT" | head -3; fi

# unparseable exits 3 (cadence no claim accounts for)
run_case "unparseable cadence exits 3" 3 "UNPARSEABLE" "" \
  "Runs 5 x week baseline." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"

# stale exits 4
TOTAL=$((TOTAL+1))
dir="$TMP/case_stale"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'runs_per_week': 2.0, 'data_end': (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=30)).isoformat(), 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "4" ] && echo "$OUT" | grep -qF "STALE"; then echo "ok   stale exits 4"; PASS=$((PASS+1)); else echo "FAIL stale (rc=$RC)"; echo "$OUT" | head -3; fi

# no claims at all exits 2
TOTAL=$((TOTAL+1))
dir="$TMP/case_noclaims"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Nothing behavioral here.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'data_end': $FRESH, 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "2" ] && echo "$OUT" | grep -qF "NO_CLAIMS"; then echo "ok   no claims exits 2"; PASS=$((PASS+1)); else echo "FAIL no claims (rc=$RC)"; echo "$OUT" | head -3; fi

# --- grammar ---
run_case "noun-after-digits range attributes to runs" 1 "DRIFT[runs_per_week]" "" \
  "3-4 runs a week is my plan." "{'runs_per_week': 1.5, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "cap is one-sided: under-cap is silent" 0 "PENDING-REVIEW" "DRIFT" \
  "Runs ≤2/wk." "{'runs_per_week': 1.5, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "cap fires over-cap" 1 "DRIFT[runs_per_week cap]" "" \
  "Runs ≤2/wk." "{'runs_per_week': 4.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "point claim within tolerance stays pending" 0 "PENDING-REVIEW" "DRIFT" \
  "Runs 2/wk." "{'runs_per_week': 2.2, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "prose frequency without activity noun stays visible" 3 "UNPARSEABLE" "DRIFT" \
  "most days I feel fine." "{'data_end': $FRESH, 'coverage_days': 28}"
run_case "prescriptive token suppresses but reports" 0 "SUPPRESSED" "DRIFT" \
  "protocol: gym 10-12x/wk target." "{'data_end': $FRESH, 'coverage_days': 28}"
run_case "prescriptive token cannot silence an unparseable cadence" 3 "UNPARSEABLE" "" \
  "protocol: runs 5 x week." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "conflicting point claims, same activity" 1 "CONFLICT[activity_point:run]" "" \
  "Runs 2/wk.
Run 5 per week now." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "different activities never conflict" 0 "PENDING-REVIEW" "CONFLICT" \
  "Runs 2/wk.
Gym 4x/week." "{'runs_per_week': 2.0, 'gym_per_week': 4.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "conflicting ranges, same activity" 1 "CONFLICT[activity_range:run]" "" \
  "3-4 runs a week.
1-2 runs a week." "{'runs_per_week': 2.5, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "sleep tolerance capped at 1.0h" 1 "DRIFT[sleep_avg_h]" "" \
  "Sleep typically 9h." "{'sleep_avg_h': 7.4, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "sleep within 1h tolerance is not drift" 0 "PENDING-REVIEW" "DRIFT" \
  "Sleep typically 8h." "{'sleep_avg_h': 7.4, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "most-days threshold is 4 active days" 1 "DRIFT[FREQUENCY]" "" \
  "Most days I exercise." "{'active_days_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "unit-less range parses as attributed range" 0 "PENDING-REVIEW" "DRIFT" \
  "Training: 3-4 sessions/wk." "{'sessions_per_week': 3.6, 'data_end': $FRESH, 'coverage_days': 28}"
run_case "missing metric is UNVERIFIED not drift" 0 "UNVERIFIED" "DRIFT" \
  "Runs 2/wk." "{'active_days_per_week': 5.0, 'data_end': $FRESH, 'coverage_days': 28}"

# --- scan ledger (guard #1: lines the grammar cannot see stay visible) ---
# needle is the ledger ENTRY form ([file:line|NO-SITE]), not the footer word
# "NO-SITE line" — a footer match would make this case vacuously green.
run_case "zero-site line appears in the ledger" 0 "[MEMORY.md:1|NO-SITE]" "" \
  "most days I feel fine.
Runs 2/wk." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"

# --- coverage-aware contract: the engine PRINTS coverage_days on the pending path ---
TOTAL=$((TOTAL+1))
dir="$TMP/case_coverage"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 3/wk.\n' > "$dir/memories/MEMORY.md"
# The source reports a coverage-honest rate (its own job); the engine's job is to
# SURFACE coverage_days so the reviewer can sanity-check it (SKILL.md contract).
make_source "$dir/sources" "{'runs_per_week': 3.25, 'data_end': $FRESH, 'coverage_days': 13}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -qF "coverage_days: 13"; then echo "ok   coverage_days surfaced for review"; PASS=$((PASS+1)); else echo "FAIL coverage (rc=$RC)"; echo "$OUT" | head -3; fi

# --- run/running conflict bucketing (round-2 finding 4) ---
run_case "runs and running conflict as one activity" 1 "CONFLICT[activity_point:run]" "" \
  "Runs 2/wk.
Running 5/wk." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
# --- lone singular claim keys to its OWN noun (unverified when source is plural) ---
run_case "lone singular Run keys to run_per_week → UNVERIFIED" 0 "UNVERIFIED[Run]" "DRIFT" \
  "Run 5 per week now." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"

# --- duration attribution: word-boundary keying; hijack and fallback are UNVERIFIED ---
TOTAL=$((TOTAL+1))
dir="$TMP/case_duration"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Sleep 9h.\n' > "$dir/memories/MEMORY.md"
# two *_avg_h metrics; the keyed one must win (not a set-order guess)
make_source "$dir/sources" "{'sleep_avg_h': 7.0, 'hrv_avg_h': 0.05, 'data_end': $FRESH, 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "1" ] && echo "$OUT" | grep -qF "DRIFT[sleep_avg_h]"; then echo "ok   duration keys to sleep_avg_h (not hrv)"; PASS=$((PASS+1)); else echo "FAIL duration (rc=$RC)"; echo "$OUT" | head -4; fi
# substring hijack: 'Sleep 9h, RHR 50.' must NOT key to rhr_avg_h silently — UNVERIFIED
TOTAL=$((TOTAL+1))
dir="$TMP/case_duration3"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Sleep 9h, RHR 50.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'rhr_avg_h': 50.0, 'sleep_avg_h': 7.0, 'data_end': $FRESH, 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if echo "$OUT" | grep -qF "UNVERIFIED[duration attribution]" && ! echo "$OUT" | grep -qF "DRIFT[rhr_avg_h]"; then echo "ok   duration hijack surfaces as UNVERIFIED"; PASS=$((PASS+1)); else echo "FAIL duration3 (rc=$RC)"; echo "$OUT" | head -4; fi
# the guessed-attribution guard is now covered by duration3 (hijack → UNVERIFIED, no DRIFT).

run_case "guessed duration attribution surfaced (exit 0, UNVERIFIED forbids clean bill)" 0 "UNVERIFIED[duration attribution]" "DRIFT" \
  "Sleep 9h, RHR 50." "{'rhr_avg_h': 50.0, 'sleep_avg_h': 7.0, 'data_end': $FRESH, 'coverage_days': 28}"
# exit-3 path surfaces hidden NO-SITE lines (soft-suppressed, no cadence)
run_case "hidden NO-SITE survives the exit-3 return" 3 "NO-SITE" "" \
  "Runs 5 x week.
Gym mornings at 6:30." "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
# bool metric value rejected (isinstance(True, int) is True — the guard must exclude bools)
TOTAL=$((TOTAL+1))
dir="$TMP/case_bool"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
printf '#!/usr/bin/env python3\nimport json, datetime\nprint(json.dumps({"runs_per_week": True, "data_end": datetime.datetime.now(datetime.timezone.utc).isoformat(), "coverage_days": 28}))\n' > "$dir/sources/s.py"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "2" ] && echo "$OUT" | grep -qF "non-numeric"; then echo "ok   bool metric rejected"; PASS=$((PASS+1)); else echo "FAIL bool (rc=$RC)"; echo "$OUT" | head -3; fi
# non-numeric metric value: SOURCE ERROR, exit 2 — never a crash-as-drift
TOTAL=$((TOTAL+1))
dir="$TMP/case_badvalue"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
printf '#!/usr/bin/env python3\nimport json, datetime\nprint(json.dumps({"runs_per_week": None, "data_end": datetime.datetime.now(datetime.timezone.utc).isoformat(), "coverage_days": 28}))\n' > "$dir/sources/s.py"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "2" ] && echo "$OUT" | grep -qF "non-numeric metric"; then echo "ok   non-numeric metric is a source error, not drift"; PASS=$((PASS+1)); else echo "FAIL badvalue (rc=$RC)"; echo "$OUT" | head -4; fi

# --- the --max-stale knob is live: a bigger gate admits older data ---
TOTAL=$((TOTAL+1))
dir="$TMP/case_staleknob"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'runs_per_week': 2.0, 'data_end': (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=15)).isoformat(), 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" --max-stale 30 2>&1); RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -qF "PENDING-REVIEW"; then echo "ok   max-stale knob admits data inside the gate"; PASS=$((PASS+1)); else echo "FAIL staleknob (rc=$RC)"; echo "$OUT" | head -3; fi

# --- freshest source wins: two sources, the fresher data_end wins ---
TOTAL=$((TOTAL+1))
dir="$TMP/case_rank"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'runs_per_week': 9.0, 'data_end': $FRESH, 'coverage_days': 28}"
printf '#!/usr/bin/env python3\nimport json, datetime\nprint(json.dumps({"runs_per_week": 2.0, "data_end": (datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=1)).isoformat(), "coverage_days": 28}))\n' > "$dir/sources/z_future.py"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "4" ] && echo "$OUT" | grep -qF "FUTURE DATA"; then echo "ok   future data_end refuses verification"; PASS=$((PASS+1)); else echo "FAIL future (rc=$RC)"; echo "$OUT" | head -4; fi
TOTAL=$((TOTAL+1))
dir="$TMP/case_rank2"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
make_source "$dir/sources" "{'runs_per_week': 9.0, 'data_end': $FRESH, 'coverage_days': 28}"
printf '#!/usr/bin/env python3\nimport json, datetime\nprint(json.dumps({"runs_per_week": 2.0, "data_end": (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=1)).isoformat(), "coverage_days": 28}))\n' > "$dir/sources/z_older.py"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
# the FRESH (s.py) source must win: runs 9.0 vs claim 2 → DRIFT, not the older 2.0
if [ "$RC" = "1" ] && echo "$OUT" | grep -qF "actual 9.0/wk"; then echo "ok   freshest source wins"; PASS=$((PASS+1)); else echo "FAIL rank2 (rc=$RC)"; echo "$OUT" | head -4; fi

# --- broken source is reported, not fatal ---
TOTAL=$((TOTAL+1))
dir="$TMP/case_broken"; mkdir -p "$dir/memories" "$dir/sources"
printf 'Runs 2/wk.\n' > "$dir/memories/MEMORY.md"
printf 'raise SystemExit(3)\n' > "$dir/sources/broken.py"
make_source "$dir/sources" "{'runs_per_week': 2.0, 'data_end': $FRESH, 'coverage_days': 28}"
OUT=$(python3 "$SCRIPT" --memory-dir "$dir/memories" --sources-dir "$dir/sources" 2>&1); RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -qF "SOURCE ERRORS"; then echo "ok   broken source reported not fatal"; PASS=$((PASS+1)); else echo "FAIL broken (rc=$RC)"; echo "$OUT" | head -4; fi

echo
echo "$PASS/$TOTAL passed"
[ "$PASS" = "$TOTAL" ]
