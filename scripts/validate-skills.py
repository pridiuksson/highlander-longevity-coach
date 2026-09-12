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
print("OK: frontmatter valid, names match directories, references resolve, Python compiles")
