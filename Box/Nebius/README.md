# Box — Nebius: a CPU coach box from zero

**Point your agent at this file.** The agent standing in front of you — Claude Code, Hermes,
Command Code, anything that can run shell commands — executes it top to bottom. When it needs
something only a human has (a login, a key, a decision), it stops at a **⛔ stop-point** and asks.
You do four things by hand; the agent does the rest.

What you get: a small Ubuntu VM on Nebius running the Hermes agent, with this kit's skills
installed, verified, and configured — ready for the personal half of
[ONBOARDING.md](../../ONBOARDING.md) (steps 7–9).

What it costs: one 2-vCPU / 8-GiB instance (`cpu-d3`, `2vcpu-8gb`) plus a 50 GiB disk, billed
hourly until you delete it. Teardown is a section of this file, not an afterthought — a forgotten
box is a standing bill.

---

## Before you start (human)

| Need | Why |
|---|---|
| A Nebius account, and your **project ID** from the console | everything the CLI creates lands in one project |
| A browser, on this machine or any machine | two logins happen at ⛔ stop-points: Nebius federation, and your model provider |
| A GitHub credential that can read this **private** repo | the box clones it at B4 — `gh` device flow or a PAT, decided now (see B4) |
| A terminal with an agent in it | the executor. If you are reading this without one, install your agent first |
| ~30–60 minutes | most of it is the agent waiting on installs and a first boot |

Nothing else — no Terraform, no container runtime, no GPU quota. The box is deliberately small.

## Variables — set these once, at the top

The run needs exactly these values. The agent substitutes them everywhere below; nothing else is
editable. Use these angle-bracket forms only — never `<YOUR_…>`-style tokens (repo convention,
see [CONTRIBUTING.md](../../CONTRIBUTING.md)).

| Variable | Default | Notes |
|---|---|---|
| `<PROJECT_ID>` | — | from the Nebius console; required, no default |
| `<REGION>` | `eu-north1` | where the box lives |
| `<VM_NAME>` | `coach-box` | the instance name |
| `<VM_USERNAME>` | `coach` | the SSH user the cloud-init creates |
| `<SSH_KEY_PATH>` | `~/.ssh/nebius-coach` | ed25519 keypair created at A4; the **private key never leaves this machine** |
| `<STATE_FILE>` | `~/.coach-box-state.env` | the run's single source of truth (written at A7) |
| `<TIMEZONE>` | — | IANA name (`Europe/Stockholm`…), used at B6 |
| `<VM_ID>`, `<PUBLIC_IP>` | — | discovered at A6/A7, recorded to `<STATE_FILE>`, never hand-set |

**Rule for the executing agent — resolve before you run:** before A1, resolve every variable with the human (`<PROJECT_ID>` and `<TIMEZONE>` have no default) and treat them as constants for the rest of the run. Discovered values land in `<STATE_FILE>` at A7; Phase B re-reads them from there, so a restarted agent loses nothing.

---

## Phase A — on your machine

### A1 — preflight

```bash
curl --version && jq --version && git --version && ssh -V
```

All four must respond. `jq` is the only one the box does not strictly need but the run does (IP
extraction). macOS and Ubuntu are the supported hosts for this phase.

### A2 — install the Nebius CLI

```bash
curl -sSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash
nebius version
```

Official installer instructions: [docs.nebius.com/cli/install](https://docs.nebius.com/cli/install/).
If `nebius` is not found after install, open a new shell or re-source your profile.

### A3 — ⛔ authenticate (human: browser)

The agent runs `nebius profile create` and **stops**. You complete the federation login in the
browser, and supply `<PROJECT_ID>` when prompted. Configuration reference:
[docs.nebius.com/cli/configure](https://docs.nebius.com/cli/configure/).

Verify before moving on:

```bash
nebius profile list        # must show the new profile as [default]
```

### A4 — SSH keypair

```bash
[ -f <SSH_KEY_PATH> ] || ssh-keygen -t ed25519 -N "" -f <SSH_KEY_PATH>
```

An existing key at that path is reused, not overwritten. The agent works with the **path** only —
the private key is never printed, copied, or sent anywhere; its public half goes into the
cloud-init user-data at A6. Background: [Nebius SSH keys](https://docs.nebius.com/compute/virtual-machines/ssh-keys/).

### A5 — find the subnet

```bash
nebius vpc subnet list --format json   # resolve exact flags with --help first
```

Take the id of the first subnet in the default network for `<REGION>`. Record nothing yet — A7
writes the state file.

### A6 — create the VM

Compose `nebius compute instance create` **after** running `nebius compute instance create --help`.
The shape the command must produce:

- platform `cpu-d3`, preset `2vcpu-8gb` (the smallest sane CPU-only shape)
- boot disk: 50 GiB `network_ssd`, image family `ubuntu24.04-driverless`
  ([images](https://docs.nebius.com/compute/storage/boot-disk-images/))
- one network interface **with a public IP**
- SSH access via cloud-init user-data creating user `<VM_USERNAME>` with the A4 public key:

```yaml
# #cloud-config
users:
  - name: <VM_USERNAME>
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - <contents of <SSH_KEY_PATH>.pub>
ssh_pwauth: false
```

Name the instance `<VM_NAME>`. Quickstart for orientation:
[docs.nebius.com/compute/quickstart](https://docs.nebius.com/compute/quickstart/).

> **Rule for the executing agent:** every Nebius command in this cookbook is a *shape*, not a
> verified flag list. Nebius' CLI moves faster than any checked-in doc — before composing each
> create/manage command, run it with `--help` and resolve the exact flags. The cookbook pins
> platform names, preset names, image families, and the order of operations; it does not pin
> flag spellings.

### A7 — wait for RUNNING, then write the state file

```bash
nebius compute instance get --id <VM_ID>    # poll until status RUNNING (typically 3–5 min)
```

Extract the public IP from the instance description (jq; resolve the exact field path against
real output). Then write `<STATE_FILE>` — every later step reads it, so the run survives an agent
restart:

```bash
cat > <STATE_FILE> <<EOF
VM_ID=<VM_ID>
PUBLIC_IP=<PUBLIC_IP>
SSH_KEY_PATH=<SSH_KEY_PATH>
VM_USERNAME=<VM_USERNAME>
REGION=<REGION>
TIMEZONE=<TIMEZONE>
EOF
chmod 600 <STATE_FILE>
```

The rule: `<STATE_FILE>` carries everything Phase B consumes — if a later step needs a value, it
reads the file, not the agent's memory.

If the instance never reaches RUNNING: serial console
([connect](https://docs.nebius.com/compute/virtual-machines/connect/)), then delete (teardown
section) and retry A6 once before investigating.

---

## Phase B — on the box

**Host-side first.** In the local terminal — the Nebius CLI and its login exist **only on the
host, never on the box** — re-read `<STATE_FILE>` and re-verify `PUBLIC_IP` and `VM_ID` against
`nebius compute instance get --id <VM_ID>` before the first SSH. Verify, don't trust; if the
agent died mid-run, this is where it resumes cleanly.

Then: `ssh -i <SSH_KEY_PATH> <VM_USERNAME>@<PUBLIC_IP>`.

**Run box commands through `bash -lc '…'`.** Ubuntu's `~/.bashrc` returns early in
non-interactive shells, so `ssh host 'source ~/.bashrc && …'` silently skips PATH setup and
`hermes` is "not found". A login shell sources `~/.profile` and gets it right.

### B1 — base packages + gitleaks

```bash
sudo apt-get update
sudo apt-get install -y curl git xz-utils jq
```

Install `gitleaks` from the official GitHub release binary (pin a major, verify the checksum
against the release's `checksums.txt`). Verify: `gitleaks version` — ONBOARDING step 4's leak gate
exits `2` without it, and an exit-2 "clean" is not a clean.

### B2 — install Hermes, headlessly

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-setup --skip-browser --skip-computer-use
bash -lc 'hermes --version'
```

Require **≥ 0.21.2**: the kit is validated on v0.21.0, but 0.21.0 has a known state.db fragility
fixed in 0.21.2 — no reason to ship a new box on the older one. Install reference:
[Hermes installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation/).

### B3 — ⛔ model credentials (human: browser or key)

The box has no browser; the human does. Pick **one**:

| Option | How |
|---|---|
| **Nous Portal** (recommended first box) | agent runs `hermes setup --portal`; it prints an OAuth URL — **open it on your laptop**, approve, return |
| **Bring your own** | run `hermes model` and follow its prompts (interactive; fine over SSH) |
| **Nebius Token Factory** | human creates an API key in the Nebius console and pastes it once at the stop-point into `~/.hermes/.env` as `NEBIUS_API_KEY`, then `hermes model` to select the provider |

Keys are typed by the human at the stop-point; they are never echoed into logs, the runbook, or
this file. Then Hermes' own first-run rule — **one clean chat** before anything else. If it does
not respond cleanly, `hermes doctor` before touching anything else.
Quickstart: [getting started](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/).

### B4 — ⛔ clone the kit (human: one credential decision, made at preflight)

The repo is **private**. Exactly one of:

- **`gh` device flow** (no PAT to manage): install `gh`, run `gh auth login`, choose HTTPS — it
  prints a one-time code and URL; **open them on your laptop**, enter the code, done.
- **PAT**: a fine-grained token with read on this repo, pasted once as the clone password.

```bash
git clone https://github.com/pridiuksson/highlander-longevity-coach ~/highlander-longevity-coach
cd ~/highlander-longevity-coach && git rev-parse HEAD    # record: this is the version on the box
```

A 404 here means the credential lacks read access — it is not a network problem.

### B5 — ONBOARDING steps 2–4, verbatim

Execute [ONBOARDING.md](../../ONBOARDING.md) steps 2, 3 and 4 exactly as written, in order:
inventory + backup, collision check (expect **some** on a fresh install — Hermes seeds bundled
skills; decide deliberately, per the doc), install, gateway restart + status, then both gates
(`leak-scan.sh`, `validate-skills.py`) and the `--installed` check. Do not paraphrase the commands;
the doc's versions carry the flags that make them safe.

### B6 — ONBOARDING step 5, configured for this box

```bash
hermes config set skills.config.health.health_dir   ~/health
hermes config set skills.config.health.baseline_doc ~/health/baseline.md
hermes config set skills.config.proactive.timezone  <TIMEZONE>
hermes config set skills.config.proactive.quiet_hours "08:00-21:00"
```

The "not a recognized config key" warning is expected — it saves anyway (ONBOARDING step 5
explains why). Override the quiet hours here if you already know better.

### B7 — ⛔ handback (human takes over)

The automated run ends here. **Do not continue into personal data** — steps 7–9 are yours, with
the agent narrating. Print this exact to-do:

1. **Instantiate a profile** (ONBOARDING step 7): copy `Profile/Maria`, `Profile/Olle` or
   `Profile/Els`; place `SOUL.md` → `~/.hermes/SOUL.md`, `USER.md`/`MEMORY.md` →
   `~/.hermes/memories/`; fill the angle-bracket fields with **your** facts; delete what does not
   apply.
2. **First run** (ONBOARDING step 8): import → verify → deliberate → interpret, then the profile
   gate question — "what are my hard constraints?" — must be answered from your profile, not
   guessed.
3. **Wire delivery** (ONBOARDING step 9): pick a target, `hermes cron list`, accept the
   `proactive-coach` suggestion (`/suggestions accept 1`) only after the target exists.

---

## Teardown

```bash
nebius compute instance delete --id <VM_ID>
```

Resolve exact flags with `--help`
([delete](https://docs.nebius.com/compute/virtual-machines/delete/)). The box's data — health dir,
memories, profile — lives on the boot disk and goes with it. Want it back later? Snapshot the
disk **before** deleting. Note that a merely *stopped* instance still bills for its disk and IP;
deleting is the only full stop.

Keep `<STATE_FILE>` until you are certain the box is gone, then delete it too — it contains no
secrets, but a stale IP/ID pair invites confusion later.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `ssh` refused right after A7 | cloud-init is still provisioning — wait ~1 min and retry; serial console if it persists |
| `leak-scan.sh` exits `2` | gitleaks missing on the box — go back to B1 |
| Gateway ignores newly installed skills | catalogue cache — `hermes gateway restart` (ONBOARDING step 3) |
| `git clone` 404s | credential lacks repo read — B4, not networking |
| `nebius` rejects a flag from this file | flag drift, the expected kind — re-run `--help` and re-resolve (top rule) |
| OAuth URL "doesn't work" | it printed on the headless box — open it on your laptop, not over SSH |
| `hermes --version` < 0.21.2 | re-run the installer without `--skip-setup`, or pin per its docs; do not onboard onto 0.21.0 |

## Doc anchors

- Nebius: [CLI install](https://docs.nebius.com/cli/install/) · [configure](https://docs.nebius.com/cli/configure/) · [compute quickstart](https://docs.nebius.com/compute/quickstart/) · [instance management](https://docs.nebius.com/compute/virtual-machines/manage/) · [SSH keys](https://docs.nebius.com/compute/virtual-machines/ssh-keys/) · [connect](https://docs.nebius.com/compute/virtual-machines/connect/) · [boot disk images](https://docs.nebius.com/compute/storage/boot-disk-images/) · [delete](https://docs.nebius.com/compute/virtual-machines/delete/)
- Hermes: [repo](https://github.com/NousResearch/hermes-agent) · [installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation/) · [quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/) · [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
- This kit: [ONBOARDING.md](../../ONBOARDING.md) · [AGENTS.md](../../AGENTS.md) · [CONTRIBUTING.md](../../CONTRIBUTING.md)

Other providers are out of scope for this file — `Box/` is the extension point. Add a sibling
directory with the same shape if you bring the kit up elsewhere.
