#!/usr/bin/env python3
"""reality_check.py — memory reality-concordance engine (enumerator + diff, never verdict).

Design contract (see SKILL.md — synthesized from a 4-round adversarial design review
plus 3 rounds of code review):

This engine ENUMERATES behavioral claim sites in memory files and DIFFS each site
against reality signatures supplied by pluggable sources. It NEVER prints "CONGRUENT":
the only safe machine verdicts are DRIFT and CANNOT-VERIFY. A clean bill of health is
concluded by the agent/human reviewing every enumerated site against the quoted actual
value (the evidence-loop trust contract) — the engine's output is an input to that
review, never its replacement.

Why: the engine's design was distilled from a reality-concordance watchdog proven in
private use over eight adversarial review rounds. Its worst defects there were not
unparsed lines — they were MIS-ATTRIBUTED claims (a parsed claim diffed against the
wrong metric) producing silent, confident "congruent" verdicts. A grammar that
silently mis-parses is worse than a human who reads the report. So the grammar here
is deliberately narrow (six generic cadence shapes), unknown attributions fail closed
as UNPARSEABLE or UNVERIFIED, and every behavioral line is accounted for — including
lines with zero enumerated sites.

Exit contract (consumed by a weekly cron; do not widen without updating SKILL.md):
  0 = enumeration emitted; sites pending agent/human review (PENDING-REVIEW, NOT clean)
  1 = drift detected (report printed; unparseable + NO-SITE evidence printed too)
  2 = no data (no source produced usable signatures; unparseable data_end counts here)
  3 = UNPARSEABLE behavioral lines (fail-closed: the grammar missed a cadence)
  4 = STALE data, a FUTURE data_end (bad source clock), or unprovable freshness

Additional printed sections that are NOT exits:
  UNVERIFIED  — a claim whose metric no source provides (or whose attribution is
                ambiguous). UNVERIFIED > 0 FORBIDS a clean bill (SKILL.md rule).
  SUPPRESSED  — lines carrying a prescriptive/protocol token; reported, never silently
                dropped: one prepended word must not blind the watchdog.
  NO-SITE     — behavioral lines the grammar saw but could not parse into sites; the
                reviewer must account for them before any clean bill.
  SCAN-LEDGER — every behavioral-line hit with its site count.

Reality sources: each *.py in the configured sources dir (config key
health.reality_sources_dir) must print a JSON dict to stdout:
  {"<kind>": <number>, ..., "data_end": "<ISO 8601>", "coverage_days": <int>}
Every metric value must be a number (non-numeric → the source is a SOURCE ERROR, never
drift). The engine ranks sources by data_end (freshest wins; same day → source
filename), validates freshness, and refuses to invent coverage. It CANNOT validate
that a source's coverage_days is honest — a documented limitation, not a fixable one.

Usage:
  python3 reality_check.py [--memory-dir DIR] [--sources-dir DIR]
                           [--max-stale DAYS] [--quiet] [--demo]
  --demo: writes an obviously-fake signatures file + memory to a temp dir and runs
          end-to-end there (no repo data file is ever shipped or read by default).

Environment (test seams, mirroring the source engine's MRC_* pattern):
  MRC_MEMORY_DIR, MRC_SOURCES_DIR — set by the regression suite.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ENGINE = "reality_check.py"
VERSION = "1.1.0"

MAX_STALE_DAYS = 10

# ---- claim grammar (narrow, generic; unknown attributions fail closed) ----
# Each pattern: (kind, regex). The grammar is an ENUMERATOR: it proposes sites; it
# never decides congruence.

# "3-4x/wk" — bare unit range: digits, optional x, then the unit phrase.
# NOTE: the unit noun is NOT captured — the reviewer attributes this range (surfaced as
# UNVERIFIED[range] when ambiguous). "3-4 sessions/wk" matches RANGE_BEFORE_NOUN below
# (which captures the noun); this pattern catches the bare "3-4x/wk" form.
RANGE_UNIT_AFTER = re.compile(
    r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:×|x)?\s*(?:/|per\s*|a\s*)(?:wk|week|day)\b", re.I)
# "3-4 runs a week" — range with the noun AFTER the digits and the unit phrase after the noun
RANGE_BEFORE_NOUN = re.compile(
    r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+(runs?|running|sessions?|workouts?|trainings?)\b"
    r"[^.]{0,15}?(?:/|per\s*|a\s*)(?:wk|week)\b", re.I)
# "runs ≤2/wk" / "runs < 2 per week" — one-sided cap
CAP = re.compile(
    r"\b(runs?|running|sessions?|workouts?|trainings?)\b[^.]{0,20}?"
    r"(?:≤|<=|=<|<)\s*(\d{1,2})\s*(?:/|per\s*|a\s*)(?:wk|week)\b", re.I)
# "runs 2/wk" / "gym 4x per week" — point claim (activity noun generic, not health-specific)
POINT = re.compile(
    r"\b(runs?|running|sessions?|workouts?|trainings?|gym)\b[^.]{0,20}?"
    r"(\d{1,2})\s*(?:×|x)?\s*(?:/|per\s*|a\s*)(?:wk|week)\b", re.I)
# "4 days a week" — frequency without a per-unit rate (integer only; "4-5" is NOT this)
DAYS_A_WEEK = re.compile(r"\b(\d{1,2})\s*days a week\b", re.I)
# "most days" — frequency without a number (needs the training context to be a claim)
MOST_DAYS = re.compile(r"\bmost days\b", re.I)
# "sleep 7.5h" / "sleeping 7.5 hours" — duration claims, noun-before-number only
# (the number-first form "7.5 hours of sleep" is a documented blind spot, see SKILL.md)
DURATION_H = re.compile(r"\bsleep(ing)?\b[^.]{0,20}?(\d{1,2}(?:\.\d)?)\s*(?:h|hours?|hrs?)\b", re.I)

# A frequency is only a claim candidate when a TRAINING/activity noun shares the line —
# otherwise "I feel tired most days lately" becomes a tolerance-free page. Sleep is
# deliberately EXCLUDED here: a sleep complaint ("I can't sleep most days") must never
# read as a training-frequency claim and drift against active-days.
ACTIVITY_CONTEXT = re.compile(r"\b(runs?|running|gym|train\w*|sessions?|workouts?|exercis\w*)\b", re.I)

# Lines that are never identity claims even when a frequency appears: prescriptive
# programs, superseded verdicts, headings, rules about memory itself.
HARD_SUPPRESS = re.compile(
    r"\bOBSOLETE\b|\bHISTORICAL\b|^\s*#|\bRENT RULE\b|\bprotocol\b|\bverdict\b|\battribution\b|\btrip-wire\b",
    re.I)

# Time-of-day wording is a schedule, not a frequency. It must NOT hide a line that
# carries a cadence (that made "gym 3-4x/wk in the evening" invisible in the source).
SOFT_SUPPRESS = re.compile(r"\d{1,2}[:.]\d{2}|\bevenings?\b|\bmornings?\b", re.I)

# Any weekly/daily cadence token: used by the unaccounted-cadence guard (a cadence no
# extracted claim accounts for fails closed rather than passing silently).
CADENCE = re.compile(
    r"\b(?:per|a)\s+(?:week|wk|day|month)\b|/\s*(?:wk|week|day)\b|\bx\s*/?\s*(?:wk|week)\b|\bweekly\b|\bdaily\b",
    re.I)

# A line is a behavioral-line candidate when an activity noun sits number-adjacent
# (within 40 chars of a digit), or a frequency-without-number shape appears.
BEHAVIORAL_LINE = re.compile(
    r"\b(runs?|running|gym|sleep|training|workouts?|sessions?|exercis\w*)\b[^.]{0,40}?\d"
    r"|\d[^.]{0,12}?\b(runs?|gym|exercis\w*)\b"
    r"|most days|\d{1,2}\s*days a week",
    re.I)

# prose counts of occasions ("3 times this week") are observations, not cadences
PROSE_COUNT = re.compile(r"\b(?:times|occasions)\s+(?:this|last|next)\s+(?:week|month|year)\b", re.I)

PATTERN_LIST = [
    ("activity_range", RANGE_UNIT_AFTER),
    ("activity_range", RANGE_BEFORE_NOUN),
    ("activity_cap", CAP),
    ("activity_point", POINT),
    ("days_per_week", DAYS_A_WEEK),
    ("most_days", MOST_DAYS),
    ("duration_h", DURATION_H),
]


def _prio(kind_match):
    kind, m = kind_match
    return (0 if kind.endswith("range") else 1, m.start(), -(m.end() - m.start()))


def extract_memory_claims(memory_dir: Path):
    """Extract claim sites + the full scan ledger. Returns (claims, unparseable,
    suppressed, scan_ledger).

    scan_ledger: every BEHAVIORAL_LINE hit → {line, sites, suppressed}. Lines with
    zero sites are the guard against the grammar's blind spot: the reviewer must
    account for them, or the count does not reconcile.
    """
    claims, unparseable, suppressed, scan_ledger = [], [], [], []
    for name in ("MEMORY.md", "USER.md"):
        path = memory_dir / name
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if not BEHAVIORAL_LINE.search(line):
                continue
            hard = bool(HARD_SUPPRESS.search(line))
            line_claims, seen = [], set()
            context_rejected = False
            for kind, pat in PATTERN_LIST:
                for m in pat.finditer(line):
                    if (kind, m.span()) in seen:
                        continue
                    seen.add((kind, m.span()))
                    if kind in ("most_days", "days_per_week") and not ACTIVITY_CONTEXT.search(line):
                        context_rejected = True
                        continue
                    line_claims.append((kind, m))
            # dedupe overlapping captures of one frequency (a range also yields a point)
            kept = []
            for km in sorted(line_claims, key=_prio):
                if any(not (km[1].end() <= k2[1].start() or km[1].start() >= k2[1].end()) for k2 in kept):
                    continue
                kept.append(km)
            line_claims = kept
            entry = {"file": name, "line": i, "text": line.strip()[:160],
                     "sites": len(line_claims), "suppressed": hard}
            scan_ledger.append(entry)
            for kind, m in line_claims:
                if hard:
                    if line.strip()[:160] not in suppressed:
                        suppressed.append(line.strip()[:160])
                    continue
                claims.append({"kind": kind, "groups": m.groups(),
                               "text": line.strip()[:160], "file": name, "line": i})
            if not line_claims:
                if hard:
                    if CADENCE.search(line):
                        unparseable.append(line.strip()[:160])
                    continue
                if context_rejected or PROSE_COUNT.search(line):
                    continue
                if SOFT_SUPPRESS.search(line) and not CADENCE.search(line):
                    continue
                unparseable.append(line.strip()[:160])
            elif len(CADENCE.findall(line)) > len(line_claims):
                unparseable.append(line.strip()[:160])
    return claims, unparseable, suppressed, scan_ledger


# ---- signatures from sources ----

def _parse_iso(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def load_signatures(sources_dir: Path):
    """Run each source script, collect (name, sig) pairs. A failing source — nonzero
    exit, non-JSON stdout, missing data_end, unparseable data_end, or a NON-NUMERIC
    metric value — is reported as an error and dropped, never raised: a broken source
    must not read as drift (exit 1)."""
    out, errors = [], []
    if not sources_dir.is_dir():
        return out, [f"sources dir not found: {sources_dir}"]
    for script in sorted(sources_dir.glob("*.py")):
        try:
            proc = subprocess.run([sys.executable, str(script)], capture_output=True,
                                  text=True, timeout=120)
        except Exception as e:
            errors.append(f"{script.name}: {e}")
            continue
        if proc.returncode != 0:
            errors.append(f"{script.name}: exit {proc.returncode}: {proc.stderr.strip()[:200]}")
            continue
        try:
            sig = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            errors.append(f"{script.name}: stdout is not JSON ({e})")
            continue
        if not isinstance(sig, dict) or "data_end" not in sig:
            errors.append(f"{script.name}: no data_end in signatures dict")
            continue
        try:
            sig["_data_end_dt"] = _parse_iso(sig["data_end"])
        except Exception as e:
            errors.append(f"{script.name}: unparseable data_end ({e})")
            continue
        bad = [k for k, v in sig.items()
               if not k.startswith("_") and k not in ("data_end",)
               and (isinstance(v, bool) or not isinstance(v, (int, float)))]
        if bad:
            errors.append(f"{script.name}: non-numeric metric value(s) {bad} — a broken "
                          f"metric must not read as drift; fix the source")
            continue
        sig["_source"] = script.stem
        out.append(sig)
    return out, errors


def select_freshest(candidates):
    # Tie-break on the exact _data_end_dt (not just the day), then the source filename —
    # max() picks the LATER filename on a tie, so the alphabet is the deliberate
    # deterministic tie-breaker (documented in SKILL.md).
    return max(candidates, key=lambda s: (s["_data_end_dt"], s.get("_source", "")))


# ---- diff ----

def rel_tol(claim):
    return max(0.5, 0.25 * claim)


def _stem(noun):
    """Normalize a captured noun for CONFLICT BUCKETING only: 'Runs', 'Run' and
    'running' are one activity. Metric keys are NOT stemmed — the source contract is
    runs_per_week, and stemming it to run_per_week would orphan every honest source.
    Conflict buckets use _stem; key building uses noun.lower() (no stemming)."""
    n = noun.lower()
    if n == "running":
        return "run"
    return n.rstrip("s")


def check(sigs, claims):
    """Diff claim sites against signatures. Returns (drift, unverifiable).
    Range claims: the range IS the tolerance (±0.5 grace). Caps: one-sided.
    Duration: tolerance capped at 1.0h. most_days: >= 4 active days/wk.
    Conflicts compare (noun, value) pairs — same kind, DIFFERENT activity must
    never conflict ('Runs 2/wk' + 'Gym 4x/week' are two claims, not one conflict).
    The diff window is the source's own coverage_days (surfaced in the report);
    the engine does not re-derive rates."""
    drift, unverifiable = [], []
    by_kind = {}
    for c in claims:
        by_kind.setdefault(c["kind"], []).append(c)

    # conflicts: same noun, different values (across or within lines).
    # The noun is part of the conflict key: comparing bare numbers across activities
    # manufactured conflicts out of two unrelated claims ('Runs 2/wk' + 'Gym 4x/week').
    # The tension the reviewer flagged: bucketing stems, keying does not. A lone
    # singular 'Run 5 per week' conflicts with 'Runs 2/wk' but its own key
    # (run_per_week) may not exist → UNVERIFIED[Run]. That is CORRECT, not a bug: the
    # conflict tells the reviewer to reconcile; the UNVERIFIED tells them the singular
    # form has no metric. Both are printed; neither is silence.
    for kind in ("activity_point", "activity_cap"):
        vals = by_kind.get(kind, [])
        uniq = {(_stem(c["groups"][0]), c["groups"][1]) for c in vals}
        if len({n for n, _ in uniq}) > 1 or len({v for _, v in uniq}) > 1:
            per_noun = {}
            for n, v in uniq:
                per_noun.setdefault(n, set()).add(v)
            for n, vs in per_noun.items():
                if len(vs) > 1:
                    cited = sorted({c["text"][:60] for c in vals if _stem(c["groups"][0]) == n})
                    drift.append(f"CONFLICT[{kind}:{n}]: memory states {sorted(vs)} — reconcile: {'; '.join(cited)}")
    for kind in ("activity_range",):
        vals = by_kind.get(kind, [])
        # normalize the two shapes to (lo, hi, noun-or-None): a shapeless (lo,hi) from
        # RANGE_UNIT_AFTER must not conflict with (lo,hi,noun) from RANGE_BEFORE_NOUN
        # when the ranges are identical; when the nouns differ, each is checked alone.
        def _norm(c):
            g = c["groups"]
            return (int(g[0]), int(g[1]), _stem(g[2]) if len(g) >= 3 else None)
        per_noun = {}
        for c in vals:
            lo, hi, noun = _norm(c)
            per_noun.setdefault(noun, set()).add((lo, hi))
        for noun, ranges in per_noun.items():
            if len(ranges) > 1:
                cited = sorted({c["text"][:60] for c in vals
                                if _norm(c)[2] == noun and _norm(c)[:2] in ranges})
                label = noun or "unattributed"
                drift.append(f"CONFLICT[{kind}:{label}]: memory states {sorted(ranges)} — reconcile: {'; '.join(cited)}")

    metric_keys = {k for k in sigs if not k.startswith("_") and k not in ("data_end", "coverage_days")}

    for c in by_kind.get("activity_point", []):
        key = f"{c['groups'][0].lower()}_per_week"
        if key not in metric_keys:
            unverifiable.append(f"UNVERIFIED[{c['groups'][0]}]: '{c['text'][:80]}' — no source reports {key}")
            continue
        claim = int(c["groups"][1])
        actual = round(float(sigs[key]), 1)
        if abs(actual - claim) > rel_tol(claim):
            drift.append(f"DRIFT[{key}]: memory says ~{claim}/wk ('{c['text'][:80]}'); actual {actual}/wk (data_end {sigs['data_end'][:10]})")

    for c in by_kind.get("activity_cap", []):
        key = f"{c['groups'][0].lower()}_per_week"
        if key not in metric_keys:
            unverifiable.append(f"UNVERIFIED[{c['groups'][0]} cap]: '{c['text'][:80]}' — no source reports {key}")
            continue
        cap = int(c["groups"][1])
        actual = round(float(sigs[key]), 1)
        if actual > cap + 0.5:
            drift.append(f"DRIFT[{key} cap]: memory says ≤{cap}/wk ('{c['text'][:80]}'); actual {actual}/wk")

    for c in by_kind.get("activity_range", []):
        groups = c["groups"]
        if len(groups) >= 3:  # RANGE_BEFORE_NOUN: (lo, hi, noun)
            lo, hi, noun = int(groups[0]), int(groups[1]), groups[2]
        else:  # RANGE_UNIT_AFTER: (lo, hi) — noun attribution is the reviewer's call
            lo, hi, noun = int(groups[0]), int(groups[1]), None
        if noun is None:
            # A bare range cannot be attributed: the reviewer resolves it. Surface
            # it as unverifiable rather than guessing a metric (no false DRIFT).
            unverifiable.append(f"UNVERIFIED[range]: '{c['text'][:80]}' — range has no activity noun; "
                                f"resolve the metric during review (lo={lo}, hi={hi})")
            continue
        key = f"{noun.lower()}_per_week"
        if key not in metric_keys:
            unverifiable.append(f"UNVERIFIED[{noun} range]: '{c['text'][:80]}' — no source reports {key}")
            continue
        actual = round(float(sigs[key]), 1)
        if actual < lo - 0.5 or actual > hi + 0.5:
            drift.append(f"DRIFT[{key}]: memory says {lo}-{hi}/wk ('{c['text'][:80]}'); actual {actual}/wk")
        elif actual < lo or actual > hi:
            drift.append(f"NOTE[{key}-BORDER]: memory says {lo}-{hi}/wk; actual {actual}/wk sits just outside — review against tolerance intent")

    for c in by_kind.get("days_per_week", []):
        key = "active_days_per_week"
        claim = int(c["groups"][0])
        if key not in metric_keys:
            unverifiable.append(f"UNVERIFIED[FREQUENCY]: '{claim} days/week' ('{c['text'][:80]}') — no source reports {key}")
            continue
        actual = round(float(sigs[key]), 1)
        if abs(actual - claim) > rel_tol(claim):
            drift.append(f"DRIFT[FREQUENCY]: memory says {claim} days/wk ('{c['text'][:80]}'); actual ~{actual}/wk")

    for c in by_kind.get("most_days", []):
        key = "active_days_per_week"
        if key not in metric_keys:
            unverifiable.append(f"UNVERIFIED[FREQUENCY]: 'most days' ('{c['text'][:80]}') — no source reports {key}")
            continue
        if float(sigs[key]) < 4:
            drift.append(f"DRIFT[FREQUENCY]: memory says training 'most days' ('{c['text'][:80]}'); actual ~{sigs[key]} active days/wk")

    for c in by_kind.get("duration_h", []):
        claim = float(c["groups"][1])
        matches = sorted(k for k in metric_keys if k.endswith("_avg_h"))
        if not matches:
            unverifiable.append(f"UNVERIFIED[SLEEP]: '{c['text'][:80]}' — no source reports an *_avg_h metric")
            continue
        # Deterministic attribution: prefer the key whose stem appears as a WORD in the
        # claim line ('sleep 7.5h' → sleep_avg_h). Substring matching hijacked claims to
        # unrelated metrics ('Sleep 9h, RHR 50' keyed to rhr_avg_h) — the silent
        # mis-attribution class this engine must never produce. Word-boundary matching
        # plus a single-match rule: ONE keyed candidate is trusted; zero or several →
        # the diff is surfaced as UNVERIFIED, never a guessed DRIFT. Residual limit: a
        # lone `*_avg_h` metric whose stem appears as a word in the line is trusted
        # even if it is the wrong metric — attribute sources carefully (SKILL.md).
        head = c["text"].lower()
        keyed = [k for k in matches
                 if re.search(rf"\b{re.escape(k.rsplit('_avg_h', 1)[0])}\b", head)]
        if len(keyed) == 1:
            key = keyed[0]
            actual = float(sigs[key])
            tol = min(rel_tol(claim), 1.0)
            if abs(actual - claim) > tol:
                drift.append(f"DRIFT[{key}]: memory says ~{claim}h avg ('{c['text'][:80]}'); actual {actual}h")
        else:
            unverifiable.append(f"UNVERIFIED[duration attribution]: '{c['text'][:80]}' — "
                                f"{len(matches)} duration metric(s) ({', '.join(matches)}), "
                                f"{len(keyed)} match the claim's words; attribute during review "
                                f"and diff manually (values: {', '.join(f'{k}={sigs[k]}' for k in matches)})")
    return drift, unverifiable


def _write_demo(tmpdir: Path):
    (tmpdir / "memories").mkdir()
    (tmpdir / "memories" / "MEMORY.md").write_text(
        "# Demo memory (obviously fake)\n"
        "Training: 3-4 sessions/wk, most days active.\n"
        "Runs OPTIONAL ≤2/wk. Sleep typically 7.5h.\n")
    sources = tmpdir / "sources"
    sources.mkdir()
    (sources / "demo_source.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, datetime\n"
        "now = datetime.datetime.now(datetime.timezone.utc)\n"
        "print(json.dumps({'sessions_per_week': 3.6, 'active_days_per_week': 5.0,\n"
        "                  'sleep_avg_h': 7.4, 'data_end': now.isoformat(),\n"
        "                  'coverage_days': 28}))\n")
    return tmpdir


def main():
    ap = argparse.ArgumentParser(description=ENGINE)
    ap.add_argument("--memory-dir", default=os.environ.get("MRC_MEMORY_DIR", ""))
    ap.add_argument("--sources-dir", default=os.environ.get("MRC_SOURCES_DIR", ""))
    ap.add_argument("--max-stale", type=int, default=MAX_STALE_DAYS)
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the ledger detail; the verdict banner and exit code are unchanged")
    ap.add_argument("--demo", action="store_true", help="run end-to-end against an obviously-fake temp fixture")
    a = ap.parse_args()

    print(f"[{ENGINE} v{VERSION}]")
    if a.demo:
        tmpdir = Path(tempfile.mkdtemp(prefix="reality_check_demo_"))
        _write_demo(tmpdir)
        a.memory_dir = str(tmpdir / "memories")
        a.sources_dir = str(tmpdir / "sources")

    memory_dir = Path(a.memory_dir).expanduser() if a.memory_dir else Path.home() / ".hermes/memories"
    sources_dir = Path(a.sources_dir).expanduser() if a.sources_dir else None
    # sources_dir=None means "not configured": the config key health.reality_sources_dir
    # is injected by Hermes as [Skill config]; standalone runs pass --sources-dir.
    # No default inside the skill tree (a user source there would be scanned by the
    # leak gate and merged over on reinstall).

    candidates, source_errors = load_signatures(sources_dir) if sources_dir else ([], ["no sources dir configured"])
    if candidates:
        sigs = select_freshest(candidates)
        # Precise age in days (ceiling), not .days truncation: 10.9 days must read as
        # STALE, not pass a 10-day gate. A FUTURE data_end (bad source clock) is refused
        # outright — "data from tomorrow" is not fresh data, and a source whose clock is
        # ahead would otherwise outrank every honest source forever.
        age_exact = (datetime.now(timezone.utc) - sigs["_data_end_dt"]).total_seconds() / 86400.0
        if age_exact < 0:
            print(f"FUTURE DATA: data_end {sigs['data_end']} is in the future — the source's clock is wrong.")
            print("A future timestamp must not read as fresh. Fix the source; refusing to verify.")
            return 4
        age_days = int(age_exact) + (0 if age_exact == int(age_exact) else 1)
        stale_note = age_days if age_days > a.max_stale else None
    else:
        sigs, stale_note = None, None

    claims, unparseable, suppressed, scan_ledger = extract_memory_claims(memory_dir)

    if not claims and not unparseable and not suppressed:
        # Nothing parseable — but the scan ledger may still hold NO-SITE lines the
        # grammar could not see. Surface them before declaring NO_CLAIMS: the
        # fail-closed guard (a cadence the grammar missed) outranks the empty verdict.
        zero_site = [e for e in scan_ledger if e["sites"] == 0 and not e["suppressed"]]
        if zero_site:
            print("=== UNPARSEABLE BEHAVIORAL LINES ===")
            for e in zero_site:
                print("⚠️", e["text"])
            print("Behavioral-looking lines with no parseable cadence. Fix the wording or")
            print("extend PATTERN_LIST. Fail-closed: refusing to assume congruence.")
            return 3
        print(f"NO_CLAIMS: no behavioral claim read from {memory_dir} — nothing was audited.")
        print("Check the memory dir (MRC_MEMORY_DIR / --memory-dir).")
        return 2
    if not candidates:
        print("NO_DATA: no sources dir configured, or no source produced usable signatures.")
        for e in source_errors:
            print("•", e)
        return 2
    if stale_note is not None:
        print(f"STALE DATA ({stale_note}d old; gate={a.max_stale}d) — data_end {sigs['data_end']}")
        print("Stale data must not read as congruent. Refresh the source and re-run.")
        return 4

    drift, unverifiable = check(sigs, claims)
    zero_site = [e for e in scan_ledger if e["sites"] == 0 and not e["suppressed"]]

    if source_errors:
        print("=== SOURCE ERRORS (reported, not drift) ===")
        for e in source_errors:
            print("•", e)
    if suppressed:
        print("=== SUPPRESSED CLAIMS (prescriptive/protocol wording) ===")
        for s in suppressed[:10]:
            print("•", s)
        if len(suppressed) > 10:
            print(f"  ... and {len(suppressed) - 10} more")
        print("These state a frequency but carry a prescriptive token — NOT checked. Reword to audit.")
    if unverifiable:
        print("=== UNVERIFIED CLAIMS (no metric available) ===")
        for u in unverifiable:
            print("•", u)
        print("A missing metric is a source limitation, NOT drift. Any UNVERIFIED site forbids a clean bill.")
    if drift:
        print("=== DRIFT DETECTED ===")
        for d in drift:
            print("⚠️", d)
        print("Resolution: confirm with the user (testimony is the arbiter). NEVER auto-edit identity memory.")
        # Unparseable evidence must survive a drift return: the operator fixes the drift
        # and never learns the grammar also missed a cadence — the source engine's
        # lesson (drift computed BEFORE the unparseable return), kept here too.
        if unparseable:
            print("=== UNPARSEABLE BEHAVIORAL LINES (also present) ===")
            for u in unparseable:
                print("⚠️", u)
            print("Fix the wording or extend PATTERN_LIST — exit 3 fires once drift is resolved.")
        # NO-SITE lines survive the drift return too: resolving the drift without
        # accounting for the grammar's blind spots would end the review early.
        if zero_site:
            print("=== NO-SITE LINES (grammar blind spot; also present) ===")
            for e in zero_site:
                print(f"  [{e['file']}:{e['line']}|NO-SITE] {e['text']}")
            print("Account for these before any clean bill — see SKILL.md guard #1.")
        return 1
    if unparseable:
        print("=== UNPARSEABLE BEHAVIORAL LINES ===")
        for u in unparseable:
            print("⚠️", u)
        # NO-SITE lines that were silently skipped (soft-suppress with no cadence, or
        # prose-count lines) must survive the exit-3 return too — same rule as the
        # drift path: resolving one failure class must not hide another.
        hidden = [e for e in zero_site if e["text"] not in unparseable]
        if hidden:
            print("=== NO-SITE LINES (also present) ===")
            for e in hidden:
                print(f"  [{e['file']}:{e['line']}|NO-SITE] {e['text']}")
        print("The grammar missed a cadence. Fix the wording or extend PATTERN_LIST. Fail-closed.")
        return 3

    # PENDING-REVIEW: the machine cannot say congruent. The report must be SELF-CONTAINED:
    # the reviewer needs the actual values, data_end and coverage_days right here — they
    # cannot be expected to re-run sources. --quiet only drops the ledger detail, never
    # the verdict marker (a cron grepping PENDING-REVIEW must still see it on exit 0).
    site_claims = [(c["file"], c["line"], c) for c in claims]
    print("=== PENDING-REVIEW: sites enumerated, awaiting review (this is NOT a clean bill) ===")
    print(f"source: {sigs.get('_source', '?')} | data_end: {sigs['data_end']} | "
          f"coverage_days: {sigs.get('coverage_days', '?')} | review against the source's own window")
    print("actual values: " + ", ".join(f"{k}={sigs[k]}" for k in sorted(sigs)
                                        if not k.startswith("_") and k not in ("data_end", "coverage_days")))
    print(f"scan ledger: {len(scan_ledger)} behavioral line(s); {len(claims)} site(s); "
          f"{len(zero_site)} line(s) with zero sites; {len(unverifiable)} unverified")
    if not a.quiet:
        claims_by_pos = {}
        for f, ln, c in site_claims:
            claims_by_pos.setdefault((f, ln), []).append(c)
        for e in scan_ledger:
            tag = "sites=%d" % e["sites"] if e["sites"] else "NO-SITE"
            print(f"  [{e['file']}:{e['line']}|{tag}] {e['text']}")
            for c in claims_by_pos.get((e["file"], e["line"]), []):
                print(f"      site: {c['kind']} {c['groups']}")
        print("\nPer SKILL.md: review every site against the quoted actual value; account for")
        print("every NO-SITE line. Only then may the reviewing agent record a clean bill — and")
        print("never while UNVERIFIED > 0. The machine itself never prints one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
