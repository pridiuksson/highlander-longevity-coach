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
```

The installer downloads the binary, prints its path (`~/.nebius/bin/nebius`), and runs a version
check itself. **Agent note:** the installer edits rc files, but step-isolated shells never source
them — call the CLI by full path (`~/.nebius/bin/nebius`), as this runbook does. Live-tested:
installer `0.12.275` on macOS and Ubuntu.

Official installer instructions: [docs.nebius.com/cli/install](https://docs.nebius.com/cli/install/).

### A3 — ⛔ authenticate (human: browser)

```bash
~/.nebius/bin/nebius profile create \
  --profile coach-box \
  --endpoint api.nebius.cloud \
  --federation-endpoint auth.nebius.com \
  --parent-id <PROJECT_ID>
```

A browser tab opens (or the command prints the URL — open it on any machine); log in to the
Nebius console and approve. Expect `profile "coach-box" configured and activated`. The
step-by-step interactive prompts are for humans in their own terminal — an agent-driven run uses
the flags above. Configuration reference:
[docs.nebius.com/cli/configure](https://docs.nebius.com/cli/configure/).

Verify before moving on:

```bash
~/.nebius/bin/nebius profile list        # must show coach-box [default]
```

### A4 — SSH keypair

```bash
[ -f <SSH_KEY_PATH> ] || ssh-keygen -t ed25519 -N "" -C coach-box -f <SSH_KEY_PATH>
```

An existing key at that path is reused, not overwritten. The `-C coach-box` comment matters:
ssh-keygen defaults the comment to `user@local-hostname`, and the key rides into the VM's
cloud-init — a neutral comment keeps your machine's name out of it. The agent works with the
**path** only — the private key is never printed, copied, or sent anywhere; its public half goes
into the cloud-init user-data at A6. Background:
[Nebius SSH keys](https://docs.nebius.com/compute/virtual-machines/ssh-keys/).

### A5 — find the subnet

```bash
~/.nebius/bin/nebius vpc subnet list --parent-id <PROJECT_ID>
```

`--parent-id` is **required** (the profile's default does not apply). Output is YAML; take
`metadata.id` of the subnet whose `status.state` is `READY` — on a fresh project there is exactly
one, `default-subnet-…`. (`--format json|yaml|table` is a *global* option, not a subcommand flag.)
Record nothing yet — A7 writes the state file.

### A5b — quota gate (do not skip)

A fresh Nebius tenant has **zero** non-GPU vCPU quota — A6 fails with
`compute.instance.non-gpu.vcpu (limit 0, requested 2)` until you raise it. Check:

```bash
~/.nebius/bin/nebius quotas quota-allowance list --parent-id <PROJECT_ID> \
  | grep -A3 "name: compute.instance.non-gpu"
```

The list omits the limit; the console shows it. In the console → **Quotas** (region
`<REGION>`), request an increase for **`compute.instance.non-gpu.vcpu`** (8 covers this box with
headroom) and **`compute.instance.count`** (4) — both usually granted quickly for small amounts.
This gate is ⛔-adjacent: the raise is a human console action, so the agent stops here if the
quota is not confirmed. **Do not trust the VM creation form as quota evidence** — it renders
happily even at limit 0; the API rejects at submit.

### A6 — create the VM

Verify the platform and preset slugs against the live catalog, then create — the full command is
below, and it is the one this cookbook was executed with:

```bash
# discovery: confirm the slugs (presets hang off platforms; there is no `preset list`)
~/.nebius/bin/nebius compute platform list --parent-id <PROJECT_ID>
# discovery: confirm the image family (public families live in the public-images project)
~/.nebius/bin/nebius compute image list --parent-id project-e00public-images --all \
  | grep -oE "image_family: [a-z0-9.-]+" | sort -u

~/.nebius/bin/nebius compute instance create \
  --parent-id <PROJECT_ID> \
  --name <VM_NAME> \
  --boot-disk-attach-mode read_write \
  --boot-disk-managed-disk-name <VM_NAME>-boot \
  --boot-disk-managed-disk-size-gibibytes 50 \
  --boot-disk-managed-disk-type network_ssd \
  --boot-disk-managed-disk-source-image-family-image-family ubuntu24.04-driverless \
  --resources-platform cpu-d3 \
  --resources-preset 2vcpu-8gb \
  --cloud-init-user-data file://<ABSOLUTE_PATH_TO_CLOUD_INIT_YAML> \
  --network-interfaces '[{"name":"nic0","subnet_id":"<SUBNET_ID>","ip_address":{},"public_ip_address":{"static":false}}]'
```

Two live-verified gotchas:

- **Do not pass `--boot-disk-managed-disk-source-image-family-parent-id`.** Pointing it at your
  own project fails with `no image of family "ubuntu24.04-driverless" in region …` — public
  families resolve from Nebius' public project without the flag.
- `--cloud-init-user-data` accepts `file://` URLs — write the user-data to a scratch file rather
  than inlining YAML.

The cloud-init user-data creates user `<VM_USERNAME>` with the A4 public key:

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

Quickstart for orientation:
[docs.nebius.com/compute/quickstart](https://docs.nebius.com/compute/quickstart/).
> **Rule for the executing agent:** these flags were verified against CLI `0.12.275` (2026-09).
> They will drift. If `create` rejects anything, re-run it with `--help` and re-resolve before
> retrying — the flag *groups* (boot disk, network interfaces, resources) have been far more
> stable than their names.

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
| `create` fails with `compute.instance.non-gpu.vcpu (limit 0, …)` | fresh-tenant quota — A5b, request the raise in the console and re-run |
| `no image of family "…" in region …` | you passed `--boot-disk-managed-disk-source-image-family-parent-id` — drop it; public families resolve without it (A6) |
| A flag from this file is rejected | flag drift — re-run `--help` and re-resolve (A6 rule) |
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
