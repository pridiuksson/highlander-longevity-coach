# Onboarding — from clone to a working coach

This takes you from a clean Hermes box to a health coach that ingests your data, verifies it, and
reaches out when — and only when — something is worth saying.

> **Validated against Hermes Agent v0.21.0 (2026.8.31).** The skill layout and gateway behaviour
> are what this was tested on; a newer version will almost certainly work, an older one might not.

## 0. Prerequisites

| Need | Why |
|---|---|
| **Hermes agent** (v0.21.0+) | hosts the skills and the loops |
| **Python ≥ 3.11** (tested on 3.12) | import/analysis scripts |
| `sqlite3` CLI | inspecting imported device databases by hand |
| *optional* `fitdecode` | parsing Garmin FIT files |
| *optional* `gitleaks` | the leak gate's secrets pass |
| *optional* `command-code` / `agy` | model-independent peer review |

## 1. Clone

```bash
git clone https://github.com/pridiuksson/highlander-longevity-coach ~/highlander-longevity-coach
cd ~/highlander-longevity-coach
```

## 2. Install the skills

Hermes loads skills **by directory**, not from a package index, so copy or symlink them in:

```bash
mkdir -p ~/.hermes/skills
cp -r skills/* ~/.hermes/skills/          # a copy
# or, to track the repo live:
# ln -s "$PWD/skills/"* ~/.hermes/skills/
```

Verify they are visible:

```bash
hermes skills list
```

## 3. Sanity-check the checkout

Both should pass on a fresh clone. If either fails, do not trust the contents.

```bash
./scripts/leak-scan.sh .              # no personal data in the tree
python3 scripts/validate-skills.py .  # every skill parses and its references resolve
```

## 4. Instantiate a profile

Pick the template closest to you — see [`Profile/README.md`](./Profile/README.md).

| Template | Pick it if |
|---|---|
| `Profile/Olle/` | you want an operator that pushes back and verifies before it acts |
| `Profile/Maria/` | you are new to AI and want an assistant that explains and asks first |
| `Profile/Els/` | you are technically fluent and want coaching plus a contributor lane |

```bash
cp -r Profile/Els ~/my-profile
```

Then, before you use it:

1. **Replace every `<PLACEHOLDER>`.** Nothing should still contain angle brackets.
2. **Delete anything that does not apply.** A template with unused sections is worse than a
   shorter accurate one.
3. Put the three files where your Hermes reads `SOUL.md`, `USER.md` and `MEMORY.md`.
4. **Keep the `MEMORY.md` rent rule.** It is what stops memory turning into a landfill.

## 5. Your data stays yours

The skills expect your health data to live **in your own files**, never in this repo:

| What | Where |
|---|---|
| Baseline values (bloods, composition, goals) | `<YOUR_HEALTH_DIR>/baseline.md` |
| Imported device databases | `$HERMES_HOME/data/*.db` |

Nothing in this repository contains anyone's health data, and it should stay that way. Do not
commit your own data into a clone of it — use your own directory.

## 6. First run

1. **Import** a device export — `samsung-health-import` or `garmin-import`. Both have their own
   gate suites; both must pass before you trust the resulting database.
2. **Verify** — nothing goes into interpretation unverified. `evidence-loop` is the skill that
   enforces this, and it exists because a plausible-but-wrong number becoming standing advice is
   the failure mode that matters most.
3. **Deliberate** — `deliberate` runs the multi-expert decision process, with the health domain
   pack in `domains/health/` shaping the personas.
4. **Interpret** — `nutrition-advisory` turns evidence into recommendations; `meal-planning`
   turns constraints into actual meals.

## 7. Proactive delivery (optional, but it is the point)

Without this you have a toolkit, not a coach.

1. Read `skills/proactive/proactive-coach/SKILL.md`.
2. **Configure quiet hours and timezone** — they are configuration, not constants.
3. Schedule the weekly crunch as a cron. The prompt *is* the crunch procedure; the skill
   describes the stages, the insight-quality gate, and the ledger.
4. Expect silence most weeks. A silent sweep is a successful run.

## 8. Restart the gateway

```bash
hermes gateway restart
```

**Do not skip this.** The Telegram gateway caches the skill catalogue at startup, so new skills
are invisible until it restarts.

## Troubleshooting

| Symptom | Cause |
|---|---|
| A skill is not listed | Wrong layout. It must be `skills/<stage>/<name>/SKILL.md`. Then restart. |
| A skill is listed but will not load | Its frontmatter is invalid, or a `references/` target is missing. |
| The gateway ignores a new skill | It cached the catalogue — restart it. |
| The leak gate is red | **Do not proceed.** Read the report; it names the pattern and the line. |
