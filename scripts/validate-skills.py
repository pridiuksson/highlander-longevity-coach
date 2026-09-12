#!/usr/bin/env python3
"""Structural validation for the skills tree — the complement to the leak gate.

The leak gate answers "is any of this private?". This answers "does any of this actually work?":
frontmatter parses, name matches directory (Hermes indexes by directory), no two skills collide on
name, every locally-referenced file resolves, every shipped Python file compiles, every config key a
skill relies on is declared, and no skill carries a token that cannot resolve at load time.

TOKEN TAXONOMY (enforced here, documented in CONTRIBUTING.md)
  * substitution class — MUST NOT appear. These look like an instruction to the reader but resolve
    to nothing: `<YOUR_HEALTH_DIR>`, `<USER>`, `<PLACEHOLDER>`, ... Paths belong in
    `metadata.hermes.config`; in-skill files belong to `${HERMES_SKILL_DIR}`.
  * redaction class — allowed, and intentionally still visible. Values the sanitizer removed
    because they were somebody's measurements: `<value>`, `<VALUE>`, `<YOUR_RESTING_HR_BPM>`, ...
    Excision of every one of these is not possible without inventing data; see CONTRIBUTING.md.
  * syntax class — allowed. Metavariables in usage strings and filename patterns: `<uuid>`,
    `<prompt>`, `<name>`, `<YYYYMMDDHHMMSS>`, ...

Cross-skill pointers written as `<skill>` skill -> `references/...` are permitted by
CONTRIBUTING.md and are not treated as local references.

Usage: validate-skills.py [--installed] [root]      (default: .)
Exit: 0 clean | 1 problems found

`--installed` is for pointing at an INSTALL root (e.g. ~/.hermes) rather than this
repo. It runs only the checks that make sense for other people's skills — duplicate
names and unexpected nesting — because applying this repo's frontmatter, token and
compile rules to 140 unrelated third-party skills produces a wall of noise with the
one real finding buried inside it.
"""
import os
import pathlib
import re
import subprocess
import sys

INSTALLED = "--installed" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
root = pathlib.Path(_args[0] if _args else ".")
problems, checked = [], 0
# Directories holding progressive-disclosure data, not skill roots.
# Mirrors agent/skill_utils.iter_skill_index_files in Hermes.
SUPPORT_DIRS = {"references", "templates", "assets", "scripts",
                "__pycache__", ".git", ".archive"}

# Must resolve at load time, so they must not exist at all.
SUBSTITUTION_CLASS = re.compile(
    r"<(YOUR_HEALTH_DIR|YOUR_BASELINE_DOC|YOUR_HEALTH_DB|YOUR_TRAINING_PLAN|"
    r"YOUR_NUTRITION_PLAN|YOUR_FOOD_GUIDE|YOUR_DESIGN_DOC|YOUR_PROMPT|"
    r"YOUR_PROFILE_NAME|YOUR_PRIVATE_REPO|YOUR_GIVEN_NAME|YOUR_FAMILY_NAME|"
    r"YOUR_GITHUB_HANDLE|USER|PLACEHOLDER)>")

# Allowed, but never mid-expression: that means the sanitizer cut a number out.
CORRUPT_VALUE_RE = re.compile(r"<value>(?=[\d%→–]|-\d)|(?<=[\d%→])<value>")
# A skill must not hardcode the install root; ${HERMES_SKILL_DIR} survives any layout.
# Matches the plain form, the doubled form, and shell-default corruption like
# ${HERMES_HOME:-$HOME$HERMES_HOME} — all of which resolve to a path that may not exist.
_HERMES_VAR = r"(?:\$\{HERMES_HOME[^}]*\}|\$HERMES_HOME)"
INSTALL_ROOT_RE = re.compile(_HERMES_VAR + r"/(?:" + _HERMES_VAR + r"/)?skills/")
# Repo-relative paths that must actually exist (catches references to a tree layout
# this repo does not have, e.g. `.agents/skills/<name>/file.json`).
RELPATH_RE = re.compile(r"[`\s(](\.agents/skills/[^\s`)]+|skills/[^\s`)]+\.(?:json|md|py|sh))")
CONFIG_KEY_RE = re.compile(r"(?<![\w./-])((?:health|proactive)\.[a-z_]+)\b")


def iter_skills(base: pathlib.Path):
    """Yield (skill_file, depth) for every SKILL.md under skills/.

    Depth counts directories between `skills/` and `SKILL.md`: 1 = flat
    (`skills/<name>/`), 2 = staged (`skills/<stage>/<name>/`). Deeper means a copy
    landed inside an existing skill dir — the silent `cp -r` merge.

    Walks with followlinks=True, matching Hermes' own enumeration. A plain
    `rglob` does NOT follow symlinked directories, so on an install that symlinks
    skills in, the duplicate check below would be blind to exactly the skills most
    likely to be dangling over another copy.
    """
    skills_root = base / "skills"
    if not skills_root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(skills_root, followlinks=True):
        dirnames[:] = sorted(d for d in dirnames if d not in SUPPORT_DIRS)
        if "SKILL.md" not in filenames:
            continue
        p = pathlib.Path(dirpath) / "SKILL.md"
        rel = p.relative_to(skills_root)
        yield p, len(rel.parts) - 1


names_seen = {}
for sk, depth in iter_skills(root):
    checked += 1
    skill_dir, rel = sk.parent, sk.relative_to(root)
    text = sk.read_text()

    # This repo uses exactly two levels (`skills/<stage>/<name>/`). Deeper means a copy
    # landed inside an existing skill dir. Other installs legitimately use subcategories,
    # so this is only an error in repo mode.
    if not INSTALLED and depth not in (1, 2):
        problems.append(
            f"{rel}: unexpected nesting (depth {depth}) — a copy probably landed inside an "
            f"existing skill dir; expected skills/<name>/ or skills/<stage>/<name>/")

    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        if not INSTALLED:
            problems.append(f"{rel}: no frontmatter")
        continue
    fm = m.group(1)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    if not name:
        if not INSTALLED:
            problems.append(f"{rel}: frontmatter missing 'name'")
    else:
        if not INSTALLED and name.group(1) != skill_dir.name:
            problems.append(f"{rel}: name '{name.group(1)}' != directory '{skill_dir.name}'")
        # Same name in two dirs => Hermes silently shows ONE and shadows the other.
        # `hermes skills list` cannot detect this; nothing else catches it either.
        names_seen.setdefault(name.group(1), []).append(str(rel))

    # Everything below applies this repo's own conventions, so it is skipped in
    # --installed mode, where most skills on the box are somebody else's.
    if INSTALLED:
        continue

    if not re.search(r"^description:", fm, re.M):
        problems.append(f"{rel}: frontmatter missing 'description'")
    if not re.search(r"^license:", fm, re.M):
        problems.append(f"{rel}: frontmatter missing 'license'")

    local = re.sub(r"`[a-z0-9-]+`\s*skill\s*(?:->|→)\s*`[^`]+`", "", text)
    for ref in sorted(set(re.findall(r"`(references/[^`]+|scripts/[^`]+)`", local))):
        if not (skill_dir / ref).exists():
            problems.append(f"{rel}: dangling reference -> {ref}")

    # Every config key a skill relies on must be declared, or its value is never injected.
    declared = {k.strip().strip("'\"") for k in re.findall(r"^\s*- key:\s*(\S+)", fm, re.M)}
    for key in sorted(set(CONFIG_KEY_RE.findall(text)) - declared):
        problems.append(f"{rel}: uses config key '{key}' but does not declare it in "
                        f"metadata.hermes.config — the value is never injected")

    # Scan every text file in the skill, so references/ are covered too.
    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file() or f.suffix not in {".md", ".py", ".sh", ".json", ".yaml", ".yml"}:
            continue
        where = f"{f.relative_to(root)}"
        content = f.read_text(errors="replace")
        for tok in sorted(set(SUBSTITUTION_CLASS.findall(content))):
            problems.append(f"{where}: fill-in token <{tok}> never resolves — declare a "
                            f"metadata.hermes.config key or use ${{HERMES_SKILL_DIR}}")
        if CORRUPT_VALUE_RE.search(content):
            problems.append(f"{where}: redacted value glued to a number (<value> mid-expression) — "
                            f"excise the fragment rather than leaving a broken expression")
        for hit in sorted(set(INSTALL_ROOT_RE.findall(content))):
            problems.append(f"{where}: hardcodes the install root ({hit}) — use "
                            f"${{HERMES_SKILL_DIR}} or name the other skill")
        for hit in sorted(set(RELPATH_RE.findall(content))):
            if not (root / hit).exists():
                problems.append(f"{where}: dangling path -> {hit} (no such file in this repo)")

    for py in skill_dir.rglob("*.py"):
        if subprocess.run([sys.executable, "-m", "py_compile", str(py)], capture_output=True).returncode:
            problems.append(f"{py.relative_to(root)}: py_compile failed")

for name, where in sorted(names_seen.items()):
    if len(where) > 1:
        problems.append(f"duplicate skill name '{name}' in {len(where)} dirs "
                        f"({', '.join(where)}) — only one will load, silently")

print(f"skills checked: {checked}")
if checked == 0:
    # A validator that reports OK for an empty tree is not a detector. This is what
    # happens when the root is wrong, and it used to look exactly like success.
    print(f"PROBLEMS (1):\n  no SKILL.md found under {root}/skills — "
          f"refusing to report OK for an empty tree")
    sys.exit(1)
if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p in problems:
        print("  " + p)
    sys.exit(1)

if INSTALLED:
    print(f"OK (installed mode): {checked} skills, no duplicate names, no unexpected nesting")
    sys.exit(0)

# --- documentation consistency -----------------------------------------------------------
# Doc rot is silent: a README that names a skill that no longer exists, or links to a file that
# was renamed, is worse than no README. These checks cost nothing and catch exactly the bugs a
# sanitization pass is prone to introduce.

doc_problems = []

# 1. relative markdown links must resolve (root docs, ci/, and the profile templates)
for pattern in ("*.md", "*/*.md", "Profile/*/*.md"):
    for doc in sorted(root.glob(pattern)):
        for target in re.findall(r"\]\((\./[^)#\s]+)\)", doc.read_text()):
            if not (doc.parent / target).exists():
                doc_problems.append(f"{doc.relative_to(root)}: broken link -> {target}")

# 2. README's loop table must name only skills that exist, and every skill must appear
readme = root / "README.md"
if readme.exists():
    named = set(re.findall(r"`([a-z0-9-]+)`", readme.read_text()))
    on_disk = {p.parent.name for p, _ in iter_skills(root)}
    for s in sorted(on_disk - named):
        doc_problems.append(f"README.md: skill '{s}' exists but is not mentioned")
    for s in sorted(n for n in named if n.endswith(("-import", "-loop", "-coach", "-planning"))
                    and n not in on_disk):
        doc_problems.append(f"README.md: names skill '{s}' which does not exist")

if doc_problems:
    print(f"DOC PROBLEMS ({len(doc_problems)}):")
    for d in doc_problems:
        print("  " + d)
    sys.exit(1)
print("OK: frontmatter valid, names unique, references resolve, config keys declared, "
      "no unresolved fill-in tokens, Python compiles, docs consistent")
