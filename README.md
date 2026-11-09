# highlander-longevity-coach

![highlander logevity coach](/highlander.webp)

A **health-coach kit** for the Hermes agent: reusable skills, the coaching loop that ties them
together, and profile templates to instantiate.

It is a coach, not a dashboard. The skills collect and verify data; the loop decides what is worth
saying and learns from whether it landed.

## Hermes Plugin (contest entry)

This repo ships a native Hermes Agent plugin at `plugin/` (`name: longevity-coach`, MIT, stdlib-only, local-first, no credentials/hooks/capabilities). It registers **9 config-free skills**, **9 typed tools**, and the **`weekly-crunch` automation blueprint** — designed to do more than a prompt or skill.

**Disclosure:** health-related values referenced in prompts/tool calls are sent to whichever model provider your Hermes session uses. Data stays on your device; only referenced values leave the box, subject to your provider policy. Demo mode uses synthetic in-memory data and does not write to your live ledger or `health.db`.

## 60-second judge path (plugin-first)

1. **Install/load** the plugin from this repo’s `plugin/` subdirectory (or catalog, once listed). Verify: `hermes plugins doctor`.
2. **Run the demo crunch** (safe, synthetic, no writes). In a Hermes session say: *“Run the longevity crunch in demo mode”* (or call `coach_run_crunch` with `demo=true`).  
   Expected output includes `[DEMO / SYNTHETIC DATA — no writes to live ledger or health.db]`, an `appraisal` (quadrant), a `micro_action`, and demo ledger/recovery placeholders.
3. **Show “more than a prompt/skill”**: run `/suggestions` and accept `longevity-coach:weekly-crunch` (after setting `proactive.timezone`), **or** run a typed tool chain such as `coach_ledger_add` → `coach_ledger_report`.

Copy-paste prompts:
- *“Run the longevity crunch in demo mode.”*
- *“Use `longevity-coach:grill` to decide: should I adopt X?”*
- *“Load `longevity-coach:plan` and help me plan my week.”*

## Config (honest defaults)

Configured via plugin settings (`plugins.entries.longevity-coach.settings.*` when supported by Hermes):
- `health.db` (default `${HERMES_HOME}/data/health.db`): SQLite path used by recovery tools when `db_path` is not provided. Current tools honor this via plugin config when available, with env/default fallback.
- `health.health_dir` (default `~/health`): reserved for future plugin surfaces; **not consumed by current tools**.
- `proactive.quiet_hours` (default `08:00-21:00`, `HH:MM-HH:MM`) and `proactive.timezone` (default empty = UTC): **advisory scheduling hints**. This plugin does **not** enforce delivery timing; set timezone to avoid midnight scheduling.

**Trust model:** tools accept an optional `db_path` for flexibility. As with any Hermes tool, the active session can access files the profile can access — treat plugin tool calls like built-in file/SQLite tools.

## Full coaching loop (optional, on-disk)

The plugin is self-contained. The full proactive coaching loop is enhanced if you also install on-disk skills from this repo (`cp -r skills/* ~/.hermes/skills/`) and configure `skills.config.*`: `proactive-coach`, `stress-dialogue`, `evidence-loop`, `biometric-recovery-ledger`, `nutrition-advisory`, `wearable-health-data`. See [ONBOARDING.md](./ONBOARDING.md) (operator runbook).

## Contest demo note

`demo/run_demo.sh` is an **internal maintainer smoke test** (Hermes internals + temp `HERMES_HOME`), **not** the judged demo. Record a real Hermes UI session (<90s) showing the 60-second path above. Manifest: `plugin/plugin.yaml`.

```
skills/       the coaching skills, grouped by the stage of the loop they serve
Profile/      SOUL / USER / MEMORY templates (8 personas: Catalyst, Visionary, Operator, Scholar, Guide, Concise, Rebuilder, Protector) & 10 physiological scaffolds
Box/          provider cookbooks to stand up a coach box (agent-executed)
scripts/      the leak gate, the validator, and the authorship + value-layer checks
AGENTS.md     working guide for agents (CLAUDE.md points here)
ONBOARDING.md from clone to a working coach
CONTRIBUTING.md
```

### The loop

> **Ingest → Verify → Interpret → Decide → Plan → Deliver proactively → Learn**

| Stage | Skills |
|---|---|
| **Ingest** | `apple-health-import`, `samsung-health-import`, `garmin-import`, `wearable-health-data` |
| **Verify** | `evidence-loop`, `find-evidence`, `memory-reality-check` |
| **Interpret** | `nutrition-advisory` (on-disk) + plugin: supplement-spec-verification, meal-planning, swedish-food-nutrition |
| **Decide** | `stress-dialogue` (pre-decide triage) → `peer-review` → `grill` → `deliberate` |
| **Plan** | `plan`, `schedule-management` |
| **Deliver** | `proactive-coach` |
| **Learn** | `proactive-coach` ledger, `biometric-recovery-ledger`, `eval-health`, `loop` |
| **Onboard** | `demo` — a fresh box's tour guide: runs real skills on the user's own questions, learns the user slowly (max 3 questions per session, skip allowed), rewards every answer instantly, retires itself at graduation |

Two things make it a loop rather than a toolbox: **nothing reaches interpretation unverified**, and
the outcome of every proactive message writes back to memory. A silent week is a successful week —
`proactive-coach` exists to decide when *not* to speak.

### Contributor workflow

The `skills/workflow/` stage serves the people and agents working **on** this repo, not the coaching
loop: `commit` (leak-gated conventional commits), `create-pr` (push and open a PR without moving
HEAD), `ticket` (author an agent-ready GitHub issue), `work` (execute an issue end-to-end), and
`contributions` (send locally-proven improvements back upstream — capture the reason at edit time,
decide at a deliberate monthly check). They
end at the ship gate `@commit → @create-pr`. [AGENTS.md](./AGENTS.md) has the full flow.

## Install

See **[ONBOARDING.md](./ONBOARDING.md)**. No machine yet? Point your agent at
[Box/Nebius/](./Box/Nebius/nebius-cpu-box-cookbook.md) — it stands one up from zero, agent-executed.

## Privacy

Nothing in this repository contains personal health data. Skills take the paths they need from
`config.yaml` (`skills.config.*`, injected at load) instead of baked-in placeholders, and the
reference docs carry deliberate `<value>` redactions where the authors' measurements were removed.
The gate below enforces that over the working tree; the identity/path/health patterns also run over
the history of the ref being built — never `--all`, so one branch's content cannot fail another
branch's build. The full-history **secrets** pass is a separate `gitleaks --log-opts="--all"`, and
the repo-wide `--all` identity audit is run on purpose before a release or a history rewrite — see
[CONTRIBUTING.md](./CONTRIBUTING.md):

```bash
./scripts/leak-scan.sh .          # identity / path / health patterns + gitleaks, over the tree

git log -p HEAD -- . \
  ':(exclude)scripts/leak-patterns.tsv' ':(exclude)scripts/leak-scan.sh' \
  | ./scripts/leak-scan.sh --no-gitleaks -      # ...and over this ref's history
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the rest of the pre-push checks.

## Status

Public, pre-release. **No tagged release yet** — pin by commit (`git rev-parse HEAD`) rather than
by `main`, which moves. Validated against Hermes Agent v0.21.0 (2026.8.31). All changes land as
pull requests: `main` is branch-protected, and the leak-gate check must pass before merge.

The sanitization method and the per-file dispositions are recorded in the authoring workspace,
which is not published.

## License

MIT — see [`LICENSE`](./LICENSE).
