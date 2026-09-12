# Onboarding — from clone to a working coach

This takes you from a clean Hermes box to a health coach that ingests your data, verifies it, and
reaches out when — and only when — something is worth saying.

> **Two versions, and they are not the same thing.**
> **Hermes Agent** v0.21.0 (2026.8.31) is what this kit was validated against — check with
> `hermes --version`; a newer version will almost certainly work, an older one might not.
> **This repo** has no tagged release yet, so "latest" is whatever `main` is when you clone. Step 1
> has you record the commit: that is the only way to say what you are actually running, and the
> thing you will need to tell whether an update is safe.

## 0. Prerequisites

| Need | Why |
|---|---|
| **Hermes agent** (v0.21.0+) | hosts the skills and the loops. Verify with `hermes --version` |
| **Python ≥ 3.11** (tested on 3.12) | import/analysis scripts |
| **`git`, with access to this repo** | the repo is private; an HTTPS clone needs a credential (`gh auth login`, or a token) |
| **`gitleaks`** | **required.** It is the secrets half of the leak gate. Without it `leak-scan.sh` exits `2` rather than claiming a pass — a "clean" that never ran the secrets scan is not a clean tree |
| *optional* `sqlite3` CLI | poking at imported device databases by hand. The skills use Python's `sqlite3` stdlib, so this is a convenience, not a requirement |
| *optional* `fitdecode` | parsing Garmin FIT files. `garmin-import` pins it into the skill's own venv |
| *optional* `command-code` / `agy` | a **model-independent** peer for `peer-review`. Without one it falls back to a subagent — a second *context*, not a second *model* |

## 1. Clone — and record what you cloned

```bash
git clone https://github.com/pridiuksson/highlander-longevity-coach ~/highlander-longevity-coach
cd ~/highlander-longevity-coach
git rev-parse HEAD        # write this down. This is your version.
```

## 2. Look before you install

Hermes resolves skills **by name**. Two directories declaring the same `name:` do not both load —
one silently shadows the other, the alphabetically-first parent directory wins, and
`hermes skills list` shows one innocent-looking row either way. `cp -r` also *merges* into an
existing directory rather than replacing it.

That is fine on a clean box and dangerous on a box that already has skills (including a box that
has already run this kit). So, first: inventory, and take a backup you can actually undo.

```bash
hermes skills list
[ -d ~/.hermes/skills ] && cp -r ~/.hermes/skills ~/.hermes/skills.bak-$(date +%Y%m%d-%H%M%S)
```

Then check for collisions **before** copying anything:

```bash
# -L because some installs symlink skills in, and a plain `find` skips them silently
existing=$(find -L ~/.hermes/skills -name SKILL.md -not -path '*/.archive/*' \
           -exec grep -h '^name:' {} + | awk '{print $2}' | sort -u)
incoming=$(find ~/highlander-longevity-coach/skills -name SKILL.md \
           -exec grep -h '^name:' {} + | awk '{print $2}' | sort -u)
comm -12 <(echo "$existing") <(echo "$incoming")
```

Any output is a name that already exists on this box: that copy will be **overwritten or
shadowed**. Usually that is what you want (you are upgrading). Just decide it deliberately, and
know that the four health-import skills are the ones most likely to be already present.

If step 4 fails, or a skill regresses later, restore is the inverse:

```bash
rm -rf ~/.hermes/skills
mv ~/.hermes/skills.bak-<the-stamp-you-just-made> ~/.hermes/skills
hermes gateway restart
```

## 3. Install the skills

```bash
hermes gateway stop       # optional, but the catalogue is cached at startup — this is the clean window
mkdir -p ~/.hermes/skills
cp -r skills/* ~/.hermes/skills/
hermes gateway restart    # so the running agent can actually see them — step 8 needs this
hermes gateway status     # confirm it came back
```

The `skills/<stage>/<name>/` layout is preserved on purpose: the stage becomes the skill's
**Category** in Hermes. Do **not** symlink the skills in — see *Updating* for why.

This also installs the `skills/workflow/` stage (`commit`, `create-pr`, `ticket`, `work`). Those are
for working on the repo itself, not for coaching — see [AGENTS.md](./AGENTS.md).

## 4. Sanity-check, then confirm the install

Both must pass on a fresh clone. If either fails, do not trust the contents.

```bash
./scripts/leak-scan.sh .              # identity / path / health patterns + secrets (needs gitleaks)
python3 scripts/validate-skills.py .  # frontmatter, names, references, config keys, tokens, compile
```

Then verify what actually landed — `hermes skills list` alone is not enough, because it cannot
show you a shadowed duplicate:

```bash
python3 scripts/validate-skills.py --installed ~/.hermes   # this kit's checks, not other people's
hermes skills list | grep -E '^[0-9]+ hub-installed' \
  || echo "could not read the summary — run \`hermes skills list\` by hand (expect 17 local)"
```

`--installed` matters: without it the validator applies *this repo's* frontmatter and token rules to
every unrelated third-party skill on the box, burying the one finding that matters in noise.

## 5. Configure — you do not edit the skills

The skills read their settings from `config.yaml`, under `skills.config.*`. Set them explicitly:

```bash
hermes config set skills.config.health.health_dir   ~/health
hermes config set skills.config.health.baseline_doc ~/health/baseline.md
hermes config set skills.config.proactive.timezone  Europe/Stockholm
hermes config set skills.config.proactive.quiet_hours "08:00-21:00"
```

It will warn that `skills.config.…` is "not a recognized config key" and save it anyway. That
notice is expected — skill-declared keys are not in the static schema — and it writes to exactly the
path the skills read. Do not skip the write because of the warning.

**Do not rely on `hermes config migrate` here.** It prompts for environment-style keys, not for
`metadata.hermes.config` settings, and `hermes config show` does not list skill settings at all —
verified on v0.21.0 with a skill installed and enabled. Setting them explicitly is the reliable path.

When a skill loads, its resolved values are injected into the message as a `[Skill config]` block:

```
[Skill config (from ~/.hermes/config.yaml):
  health.health_dir = /srv/health
]
```

That is why nothing under `skills/` needs hand-editing: a clone can live anywhere, and no path is
baked into an installed file.

## 6. Your data stays yours

| What | Where |
|---|---|
| Baseline values (bloods, composition, goals) | `health.baseline_doc` — default `~/health/baseline.md` |
| Imported device databases | `health.db` — default `$HERMES_HOME/data/health.db` |
| Raw exports (Samsung / Garmin zips) | `health.health_dir/*-exports/` (gitignored) |

Nothing in this repository contains anyone's health data, and it should stay that way. Do not
commit your own data into a clone of it.

One thing to expect: the reference docs under `skills/**/references/` still carry `<value>` and a
few `<YOUR_…>` markers where the authors' own measurements were removed. Those are deliberate
redactions, not fields you are meant to fill in. See CONTRIBUTING.md for the token taxonomy.

## 7. Instantiate a profile

Pick the template closest to you — see [`Profile/README.md`](./Profile/README.md).

| Template | Pick it if |
|---|---|
| `Profile/Olle/` | you want an operator that pushes back and verifies before it acts |
| `Profile/Maria/` | you are new to AI and want an assistant that explains and asks first |
| `Profile/Els/` | you are technically fluent and want coaching plus a contributor lane |

```bash
cp -r Profile/Els ~/my-profile
```

Then:

1. **Put the three files where Hermes actually reads them** — this is the step that silently does
   nothing if you get it wrong:
   - `SOUL.md` → `~/.hermes/SOUL.md`
   - `USER.md` → `~/.hermes/memories/USER.md`
   - `MEMORY.md` → `~/.hermes/memories/MEMORY.md`

   Profile files are read as plain text, not through the skill pipeline, so they take effect on the
   next turn — no gateway restart needed for these (unlike step 3).
2. **Fill in the angle-bracket fields.** In the *profile* these are yours to write — `<USER>`,
   `<AGE>`, `<CITY>`. Unlike the skills there is no config mechanism here, because these are the
   facts about you that the whole loop is built on.
3. **Delete anything that does not apply.** A template with unused sections is worse than a shorter
   accurate one.
4. **Keep the `MEMORY.md` rent rule.** It is what stops memory turning into a landfill.

Record where this profile came from, for later: the commit from step 1 and the template you forked
(`derived_from: highlander-longevity-coach@<sha>`, `profile: Els`).

## 8. First run

1. **Import** a device export — `samsung-health-import` or `garmin-import`. Both have their own
   gate suites; both must pass before you trust the resulting database.
2. **Verify** — nothing goes into interpretation unverified. `evidence-loop` is the skill that
   enforces this, and it exists because a plausible-but-wrong number becoming standing advice is
   the failure mode that matters most.
3. **Deliberate** — `deliberate` runs the multi-expert decision process, with the health domain
   pack in `domains/health/` shaping the personas.
4. **Interpret** — `nutrition-advisory` turns evidence into recommendations; `meal-planning`
   turns constraints into actual meals.

**Gate before you go further:** confirm the profile actually loaded, not merely that the files are
placed. Ask the agent something only your profile can answer — "what are my hard constraints?"
If it does not know, revisit step 7.1.

## 9. Wire proactive delivery

The gateway was restarted at step 3, and it caches the skill catalogue at startup — so if you have
changed anything since, restart it again before expecting a message to fire.

`proactive-coach` ships a **blueprint** — a schedule declared in its frontmatter. Installing a
blueprint does *not* silently create a job; it adds a suggestion you accept:

```
/suggestions            # list pending
/suggestions accept 1   # create the weekly crunch job
```

A fresh box has no delivery target, so decide where the message should land before you accept.
`--deliver` accepts `origin`, `local`, `telegram`, `discord`, `signal`, `platform:chat_id`, or
`bot-chat[:profile]`:

```bash
hermes cron list
hermes cron edit <job_id> --deliver telegram      # same grammar as `hermes cron create`
```

Quiet hours and timezone come from step 5 (`proactive.quiet_hours`, `proactive.timezone`) — they
are configuration, not constants. Then expect silence most weeks: a silent sweep is a successful
run, and `proactive-coach` exists to decide when *not* to speak.

## Updating

The install is a copy, so an update is: pull, re-check, re-copy, restart.

```bash
cd ~/highlander-longevity-coach
git pull && git rev-parse HEAD        # new version — record it
```

1. Re-run the **collision check** from step 2. A new release can add a name that now collides with
   something on your box.
2. `cp -r skills/* ~/.hermes/skills/` — this **overwrites** the installed skills, which is what you
   want. Your settings live in `config.yaml` and your profile in `~/.hermes/{SOUL.md,memories/}`,
   so neither is touched. That is exactly why no path is hand-edited into a skill.
3. `hermes gateway restart`.

**Do not symlink the skills instead.** A symlink carries no recorded revision, so you can never
tell whether a given skill is the version you think it is, and drift becomes undetectable — which
is the failure the repo's versioning design exists to prevent.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `git clone` 404s | the repo is private. Authenticate (`gh auth login`) or use a token |
| A skill is not listed | Wrong layout. At the install root it must be `skills/<name>/SKILL.md` or `skills/<stage>/<name>/SKILL.md`. Then restart the gateway |
| A skill is listed, but the *other* version is running | Duplicate names: one shadows the other, alphabetically-first parent wins, and the list looks fine. `python3 scripts/validate-skills.py ~/.hermes` names both |
| A skill is listed but will not load | Its frontmatter is invalid, or a `references/` target is missing. The validator reports both |
| Paths inside a skill are dead | You are running an older copy that hardcoded `$HERMES_HOME/skills/<name>/`. Current ones use `${HERMES_SKILL_DIR}` and `config.yaml` — re-copy from a current checkout |
| `leak-scan.sh` exits `2` | gitleaks is missing while the secrets pass is enabled. Install it, or pass `--no-gitleaks` knowingly |
| The gateway ignores a new skill | It cached the catalogue — restart it |
| The leak gate is red | **Do not proceed.** Read the report; it names the pattern and the line |
| The weekly job never fires | Check the delivery target — a fresh box has none configured (step 9) |
