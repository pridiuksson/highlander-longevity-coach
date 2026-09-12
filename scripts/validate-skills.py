#!/usr/bin/env python3
"""Structural validation for the skills tree — the complement to the leak gate.

The leak gate answers "is any of this private?". This answers "does any of this actually work?":
frontmatter parses, name matches directory (Hermes indexes by directory), every locally-referenced
file resolves, and every shipped Python file compiles.

Cross-skill pointers written as `<skill>` skill -> `references/...` are permitted by
CONTRIBUTING.md and are not treated as local references.

Usage: validate-skills.py [root]      (default: .)
Exit: 0 clean | 1 problems found
"""
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
problems, checked = [], 0

for sk in sorted(root.glob("skills/*/*/SKILL.md")):
    checked += 1
    skill_dir, rel = sk.parent, sk.relative_to(root)
    text = sk.read_text()

    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        problems.append(f"{rel}: no frontmatter")
        continue
    fm = m.group(1)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    if not name:
        problems.append(f"{rel}: frontmatter missing 'name'")
    elif name.group(1) != skill_dir.name:
        problems.append(f"{rel}: name '{name.group(1)}' != directory '{skill_dir.name}'")
    if not re.search(r"^description:", fm, re.M):
        problems.append(f"{rel}: frontmatter missing 'description'")
    if not re.search(r"^license:", fm, re.M):
        problems.append(f"{rel}: frontmatter missing 'license'")

    local = re.sub(r"`[a-z0-9-]+`\s*skill\s*(?:->|→)\s*`[^`]+`", "", text)
    for ref in sorted(set(re.findall(r"`(references/[^`]+|scripts/[^`]+)`", local))):
        if not (skill_dir / ref).exists():
            problems.append(f"{rel}: dangling reference -> {ref}")

    for py in skill_dir.rglob("*.py"):
        if subprocess.run([sys.executable, "-m", "py_compile", str(py)], capture_output=True).returncode:
            problems.append(f"{py.relative_to(root)}: py_compile failed")

print(f"skills checked: {checked}")
if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p in problems:
        print("  " + p)
    sys.exit(1)
# --- documentation consistency -----------------------------------------------------------
# Doc rot is silent: a README that names a skill that no longer exists, or links to a file that
# was renamed, is worse than no README. These checks cost nothing and catch exactly the bugs a
# sanitization pass is prone to introduce.

doc_problems = []

# 1. relative markdown links must resolve
for doc in sorted(list(root.glob("*.md")) + list(root.glob("*/*.md"))):
    for target in re.findall(r"\]\((\./[^)#\s]+)\)", doc.read_text()):
        if not (doc.parent / target).exists():
            doc_problems.append(f"{doc.relative_to(root)}: broken link -> {target}")

# 2. README's loop table must name only skills that exist, and every skill must appear
readme = root / "README.md"
if readme.exists():
    named = set(re.findall(r"`([a-z0-9-]+)`", readme.read_text()))
    on_disk = {p.parent.name for p in root.glob("skills/*/*/SKILL.md")}
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
print(f"OK: frontmatter valid, names match directories, references resolve, Python compiles, docs consistent")
