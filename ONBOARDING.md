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
| **A machine to run on** | no box yet? Point your agent at [Box/Nebius/](./Box/Nebius/nebius-cpu-box-cookbook.md) — it stands one up from zero, stopping only where a human must act |
| **Hermes agent** (v0.21.0+) | hosts the skills and the loops. Verify with `hermes --version` |
| **Python ≥ 3.11** (tested on 3.12) | import/analysis scripts |
| **`git`, with access to this repo** | the repo is private; an HTTPS clone needs a credential (`gh auth login`, or a token) |
| **`gitleaks`** | **required.** It is the secrets half of the leak gate. Without it `leak-scan.sh` exits `2` rather than claiming a pass — a "clean" that never ran the secrets scan is not a clean tree |
| *optional, recommended* `pre-commit` framework | runs the leak gate and the value-layer check on every local commit — the only check that fires *before* a leaky commit exists. `pipx install pre-commit && pre-commit install` wires `.pre-commit-config.yaml` into git; without that step the committed hook config runs nowhere. CI and the pre-push gates still catch a leak, but at push time — fixing it then means rewriting history |
| *conditional* PCRE engine — GNU `grep` or `perl` | the gate's patterns are PCRE: GNU grep (`-P`) is used when present, else perl, else the gate exits `2` rather than guess. macOS: stock grep has no `-P`, so the pre-shipped perl is the engine — nothing to install. Linux: GNU grep is normally already there |
| *optional* `sqlite3` CLI | poking at imported device databases by hand. The skills use Python's `sqlite3` stdlib, so this is a convenience, not a requirement |
| *optional* `fitdecode` | parsing Garmin FIT files. `garmin-import` pins it into the skill's own venv |
| *optional* `command-code` / `agy` | a **model-independent** peer for `peer-review`. Without one it falls back to a subagent — a second *context*, not a second *model* |
| *optional* Honcho API key | the memory-overlay provider this kit is field-tested with — see step 5. Without it the kit runs on the local files alone |

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
hermes doctor                         # agent health; --fix migrates config versions
```

Then verify what actually landed — `hermes skills list` alone is not enough, because it cannot
show you a shadowed duplicate:

```bash
python3 scripts/validate-skills.py --installed ~/.hermes   # this kit's checks, not other people's
hermes skills list | grep -E '^[0-9]+ hub-installed' \
  || echo "could not read the summary — run \`hermes skills list\` by hand (expect 22 local: 17 coaching + 4 workflow + 1 onboarding/demo)"
```

`--installed` matters: without it the validator applies *this repo's* frontmatter and token rules to
every unrelated third-party skill on the box, burying the one finding that matters in noise.
`hermes doctor` covers the box itself — run it after installs and upgrades; `--fix` performs
config-version migrations.

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

### Memory provider (optional)

The kit's memory is three plain files — `SOUL.md`, `USER.md`, `MEMORY.md` (step 7) — plus your
`health.baseline_doc`. A memory provider layers **on top of** those files; it never replaces them.
This kit is field-tested with [Honcho](https://honcho.dev):

```bash
hermes config set memory.provider honcho
# then add HONCHO_API_KEY to ~/.hermes/.env and restart the gateway
```

Honcho prefetches relevant memories each turn and mirrors writes back — an overlay on the local
store, with **one workspace per Hermes profile** so two people on one box stay isolated. Without
it, everything in this kit runs on the local files alone.

Three field lessons (2026-08, a long-running install):

- **Saturation, not sync, is the failure mode.** When `MEMORY.md` reaches `memory_char_limit`, the
  memory tool refuses writes and the agent starts "forgetting". The rent rule in the profile
  templates is the first defense; raising the cap is the second.
- **Consoles snapshot config at launch.** After changing memory (or any) config, restart the
  gateway *and* relaunch open `hermes` consoles — a resumed console keeps the old config.
- **`hermes doctor` is the arbiter.** It reports provider/config problems; `--fix` migrates config
  versions after upgrades.

If you let the agent create skills of its own, consider `skills.guard_agent_created: true` —
autonomous skills land in the same namespace this kit installed into; re-run the step-2 collision
check whenever one appears.

## 6. Your data stays yours

| What | Where |
|---|---|
| Baseline values (bloods, composition, goals) | `health.baseline_doc` — default `~/health/baseline.md` |
| Imported device databases | `health.db` — default `$HERMES_HOME/data/health.db` |
| Raw exports (Samsung / Garmin zips) | `health.health_dir/*-exports/` (gitignored) |
| Mirrored memories (if a memory provider is configured) | the provider's store — outside this box. The local files stay the source of truth |

Nothing in this repository contains anyone's health data, and it should stay that way. Do not
commit your own data into a clone of it.

One thing to expect: the reference docs under `skills/**/references/` still carry `<value>` and a
few `<YOUR_…>` markers where the authors' own measurements were removed. Those are deliberate
redactions, not fields you are meant to fill in. See CONTRIBUTING.md for the token taxonomy.

## 7. Instantiate a profile

The bundled profiles under [`Profile/`](./Profile/) are scaffolds for different kinds of people, and
new ones get added over time. So this step is a **framework for matching, not a lookup table**:
whoever drives the onboarding — an agent working with the user, or a human alone — thinks with the
dimensions below against the *current* registry, never against a list frozen in this doc.

### Match the person to a profile

**Ask before you assume.** The driver interviews the user in one short pass, then recommends. A
human working alone answers the same questions for themselves. The questions below are the floor,
not the script — derive the discriminating ones from the registry rows:

- What do you want from Hermes — an operator that pushes back and verifies before it acts, an
  assistant that explains and asks first, or something in between?
- When something breaks, do you read the logs yourself?
- Will you work on this kit's skills, or only be coached?
- The facts that fill the template: name, age, sex, city, occupation, language, wearable device,
  training, hard constraints (injuries, intolerances, medications), and how much proactive contact
  you want.

**Enumerate candidates from the registry, not from this doc.**
[`Profile/README.md`](./Profile/README.md) holds the living list and each profile's
self-description — read every one before matching, so a profile added after this doc was written
is considered too.

**Assess on the dimensions that drive fit:**

- **Style of authority** — pushback-first, explain-first, or in between. The axis the bundled
  profiles are built around.
- **Technical fluency** — decides how much gets explained versus done, and breaks style ties.
- **Contribution intent** — some profiles carry a contributor lane, some don't.
- **Health context** — age, sex, device, constraints. These never choose the persona: they decide
  which template sections survive the delete step below, and which import skill step 8 will need.

**Recommend with a reason.** Name the closest match and say in one sentence why; offer the
runner-up. The persona is the user's call — the agent recommends and, on confirmation, does the
typing. If nothing is a clean fit, take the closest and adapt harder (step 3 below); the templates
are scaffolds, not a fixed menu.

### Adopt

```bash
cp -r Profile/<TEMPLATE> ~/my-profile
```

Then:

1. **Put the three files where Hermes actually reads them** — this is the step that silently does
   nothing if you get it wrong:
   - `SOUL.md` → `~/.hermes/SOUL.md`
   - `USER.md` → `~/.hermes/memories/USER.md`
   - `MEMORY.md` → `~/.hermes/memories/MEMORY.md`

   Profile files are read as plain text, not through the skill pipeline, so they take effect on the
   next turn — no gateway restart needed for these (unlike step 3).
2. **Fill in the angle-bracket fields from the interview answers** — `<USER>`, `<AGE>`, `<CITY>`.
   Unlike the skills there is no config mechanism here, because these are the facts about the user
   that the whole loop is built on. Never invent an answer the user did not give, and never press
   for one: a declined answer stays a placeholder, and any section that depends on it goes with
   step 3.
3. **Delete anything that does not apply, and adapt the tone.** Health sections follow the health
   facts (a cycle-tracking section survives only if it applies to this person); where the user's
   stated expectations differ from the template's defaults, bend the tone lines and record the
   delta. A template with unused sections is worse than a shorter accurate one.
4. **Keep the `MEMORY.md` rent rule.** It is what stops memory turning into a landfill.

Re-matching later — the person changes, or the registry grows — replaces only `SOUL.md`:
`USER.md` and `MEMORY.md` belong to the person and survive the swap.

**Guardrails.** Interview answers are personal data: they are written only into `~/.hermes/` on the
box, never into a clone of this repo (step 6 is the rule). The default is that the **human types
them** — the handback exists so personal facts do not pass through an agent transcript. Agent-fill
is opt-in: only when the user explicitly asks, the agent shows the filled profile as a diff for
approval before writing, and names the caveat that the answers now live in the transcript too.

Record where this profile came from, for later: the commit from step 1 and the template you forked
(`derived_from: highlander-longevity-coach@<sha>`, `profile: <name>`).

A second person on the same box is a **Hermes profile**, not a second set of memory files: each
profile under `~/.hermes/profiles/<name>/` carries its own `config.yaml`, state, gateway service,
and local memory store. Instantiate the templates per profile rather than mixing two people's
`USER.md` into one store.

## 8. First run

> **No device exports yet?** Run the step-8 gate first ("what are my hard constraints?" — it
> takes one message and confirms your profile loaded), then skip to step 10 — `demo` works
> with zero data, learns what it needs to make the kit useful today, and will tell you when
> an import becomes worthwhile. Come back here once you have an export.

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
If it does not know, revisit step 7.

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

## 10. Let it learn you

A fresh profile is a skeleton, and the kit is built to adapt to you — but it can only adapt to
what it knows. `demo` is the onboarding skill that closes this gap by *doing*: it runs real
skills on your own questions while it slowly learns the facts that make the rest of the kit
yours (diet, city, sleep window, supplements — never more than 3 questions per session, and
skip is always an option).

Run it interactively right now:

```
demo
```

Or accept its daily suggestion instead — the same `/suggestions` flow as step 9 (the skill
ships a `blueprint:` in its frontmatter, so after the step-3 gateway restart it appears as a
pending suggestion; accept it and the learn cron asks at most a couple of casual questions per
day, each answered with an immediately useful result — tell it your diet and it prices matching
staples at your local store; give it your weight and it computes your protein range). The
blueprint's prompt already encodes the guardrails: budget, quiet hours, the shared daily cap,
and silence as the correct outcome when nothing should be asked.

Everything it learns lands where the rest of the kit already reads — `health.baseline_doc`
(step 5) and `~/.hermes/memories/USER.md` — so skills pick it up with no extra wiring. When
your profile is complete (or after ~30 days, whichever comes first), it says so once, wires
the handoff to `proactive-coach`, and you never hear from it again. It holds no data of its
own beyond a progress file in `$HERMES_HOME/data/demo/`.

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
| The verdict says `value-layer: NOT-CONFIGURED` | Expected on a fresh clone, and **not** a failure: the shape patterns ran and passed, but the identity checks (your name, your handle) are not configured, and the verdict says so rather than implying coverage it does not have. Set up the value layer: `mkdir -p ~/.config/leak && cp scripts/leak-patterns.local.example.tsv ~/.config/leak/patterns.tsv`, then fill it in. It lives outside the repo on purpose — a tracked file naming those identifiers is the leak the gate exists to prevent |
| The verdict says `CONFIGURED BUT INERT` or `CONFIGURED BUT EMPTY` | The value layer exists and checks nothing: the entries are still `<YOUR_...>` placeholders, or the file has no entries. `./scripts/check-values-configured.sh` is the same check as a standalone command, and the pre-commit hook runs it |
| You had `swedish-groceries` installed | It was renamed to `swedish-food-nutrition`. The name-based collision check cannot see a rename (different `name:`), so you now have a silent functional duplicate. Retire the old directory before/after installing. Field-tested 2026-09-12: scripts are byte-identical between the two, so nothing is lost |
| `demo` keeps asking questions | Check `$HERMES_HOME/data/demo/state.json` — `budget_used` vs `budget_limit_asks`, `skip_streak`, and `stop_learning`. It must retire itself at 21 asks or 30 days; if it will not stop, say "stop learning" and verify `stop_learning` flips to `true` |
| The agent forgets things, or the memory tool refuses writes | `MEMORY.md` has saturated `memory_char_limit` — writes are refused at the cap. Apply the rent rule and raise the cap (`hermes config edit`), then restart the gateway. If a memory provider is configured, `hermes doctor` names half-configured pieces |

## Field note: adopting onto a box that already has skills (2026-09-12)

Step 2's collision check tells you *that* a name collides. It cannot tell you *which side
should win*, and it cannot see skills that live under a **renamed home** or under an **old
name**. If your box predates this kit, or you maintain customized copies of these skills:

1. Diff every collision before copying — do not assume "you are upgrading". One field test
   found three stale local copies (upstream correctly won) AND one case where **upstream was
   the stale side**: the local `plan` skill used a backend-aware relative path that an upstream
   edit had regressed to `$HERMES_HOME/plans/`. Direction of "better" is per-skill, not global.
2. Normalize placeholders before comparing (`<YOUR_...>`, `${HERMES_SKILL_DIR}` vs hardcoded
   paths) — otherwise cosmetic differences mask real ones, and vice versa.
3. Check `references/` and `scripts/` trees separately: a SKILL.md can be near-identical while
   one side carries whole reference files the other lacks.
4. A skill body that hardcodes instance paths is not "wrong" — it is pre-migration. Decide
   whether its values belong in `config.yaml` (then adopt upstream) or are genuinely
   instance-specific (then keep local and record the delta).
5. Record the decision per skill — a diff you did not write down is a diff you will re-do.

## Renames

`swedish-groceries` → `swedish-food-nutrition` (2026-09). If you installed under the old name,
retire it: the collision check in step 2 matches on `name:` and will not flag the leftover.
