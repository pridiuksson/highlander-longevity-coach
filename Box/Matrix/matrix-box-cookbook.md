# Box — Matrix: a cloud coach box via Matrix OS

**Point your agent at this file.** The agent standing in front of you — Claude Code, Hermes,
Command Code, Zed agent, or anything that can run shell commands — executes it top to bottom.
When it needs something only a human has (a login, a key, a decision), it stops at a
**⛔ stop-point** and asks. You do two things by hand; the agent does the rest.

What you get: a cloud-hosted Matrix OS computer running the Hermes agent, with this kit's skills
installed, verified, and configured — ready for the personal half of
[ONBOARDING.md](../../ONBOARDING.md) (steps 7–9).

What it costs: a Matrix OS account with an active Matrix computer instance. Matrix manages the
compute lifecycle, container runtime, code server, and terminal multiplexing.

---

## Before you start (human)

| Need | Why |
|---|---|
| A Matrix OS account at `matrix-os.com` | provides the cloud computer and gateway |
| A browser, on this machine or any machine | authentication happens at A3 via OAuth device flow |
| Node.js ≥ 20 on your local machine | required to run the Matrix CLI (`@finnaai/matrix`) |
| A terminal with an agent in it | the executor. If you are reading this without one, install your agent first |
| ~10–15 minutes | mostly agent-driven setup on the pre-provisioned computer |

---

## Variables — set these once, at the top

The run needs exactly these values. Use angle-bracket placeholders only (repo convention, see
[CONTRIBUTING.md](../../CONTRIBUTING.md)).

| Variable | Default | Notes |
|---|---|---|
| `<TIMEZONE>` | `UTC` | IANA name (`Europe/Stockholm`, `America/New_York`…), used at B6 |
| `<MATRIX_PROFILE>` | `cloud` | CLI profile name (default is `cloud`) |
| `<HEALTH_DIR>` | `~/health` | path for personal health data on the Matrix computer |

**Rule for the executing agent — resolve before you run:** confirm `<TIMEZONE>` with the human before
Phase B.

---

## Phase A — on your local machine

### A1 — preflight

```bash
node -v && npm -v && curl --version
```

Node must be ≥ 20. macOS and Linux/Ubuntu are supported hosts.

### A2 — install the Matrix CLI

The official package is `@finnaai/matrix`. On Linux hosts, install in an isolated prefix to
avoid optional macOS build dependencies (`fsevents` gyp rebuild failure):

```bash
mkdir -p ~/.local/share/finnaai-matrix
npm install --prefix ~/.local/share/finnaai-matrix @finnaai/matrix

# Link binaries into ~/.local/bin (must be in your PATH)
mkdir -p ~/.local/bin
ln -sf ~/.local/share/finnaai-matrix/node_modules/.bin/matrix ~/.local/bin/matrix
ln -sf ~/.local/share/finnaai-matrix/node_modules/.bin/matrixos ~/.local/bin/matrixos
ln -sf ~/.local/share/finnaai-matrix/node_modules/.bin/mos ~/.local/bin/mos

matrix --version
```

Expect version `0.3.21` or newer.

> **Gotcha noted:** The standalone curl installer (`curl -fsSL https://get.matrix-os.com | sh`)
> may 404 upstream. Installing via `npm` into an isolated prefix is the reliable path.

### A3 — ⛔ authenticate (human: browser)

```bash
matrix login
```

The CLI prints a one-time device code and authorization link:
```text
Visit: https://app.matrix-os.com/auth/device?user_code=XXXX-XXXX
Enter code: XXXX-XXXX
```

Open the link in your browser, log in to Matrix OS, and approve the device. The CLI will
automatically detect authorization and save your profile credentials to `~/.matrixos/`.

Verify before proceeding:

```bash
matrix whoami        # must show your handle and (cloud)
matrix status        # must report Gateway: ok, Authenticated: yes
```

### A4 — instance check

Verify that your Matrix computer is active:

```bash
matrix instance info
```

Expect a JSON response showing your instance running, CPU count, memory, and status `available`.

---

## Phase B — on the Matrix computer

Commands on the Matrix computer are driven through the Matrix CLI via:
`matrix run --project=main -C . -- <COMMAND>`

> **Agent notes on `matrix run`:**
> 1. **Always pass `--project=main -C .`**: In `@finnaai/matrix` v0.3.21, running `matrix run`
>    without a project or with an empty CWD triggers an HTTP 400 schema error on the gateway.
>    `--project=main -C .` resolves to the workspace root cleanly.
> 2. **Avoid local tilde expansion**: The local shell expands `~` to `<LOCAL_HOME>`, but
>    on the Matrix computer you want the remote user's `$HOME`. Quote remote commands or use
>    `bash -c '...'` so tilde/variable expansion happens on the Matrix machine.
> 3. **Avoid monolithic long commands**: The Matrix gateway reverse-proxy times out on single
>    HTTP calls exceeding ~30–60 seconds (HTTP 504). Keep operations modular and targeted.

### B1 — base packages + gitleaks

The Matrix computer runs Ubuntu 24.04 LTS. Python, Node.js, and git are pre-installed. Install `jq`
and pin `gitleaks` (required for the ONBOARDING step 4 leak gate):

```bash
# Install jq
matrix run --project=main -C . -- sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
matrix run --project=main -C . -- sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq jq

# Install gitleaks (pinned v8.30.1)
matrix run --project=main -C . -- curl -fsSL -o /tmp/gitleaks.tar.gz \
  https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz
matrix run --project=main -C . -- tar -xzf /tmp/gitleaks.tar.gz -C /tmp
matrix run --project=main -C . -- sudo install /tmp/gitleaks /usr/local/bin/gitleaks
matrix run --project=main -C . -- gitleaks version
```

`gitleaks version` must output `8.30.1`.

### B2 — Hermes agent & gateway setup

Hermes is pre-provisioned on the Matrix computer under `~/.hermes` with the binary
at `~/.local/bin/hermes`.

Verify the installation and enable the persistent gateway service:

```bash
matrix run --project=main -C . -- bash -lc 'hermes --version'
```

Install and start the gateway systemd service:

```bash
matrix run --project=main -C . -- bash -lc 'hermes gateway install'
matrix run --project=main -C . -- bash -lc 'hermes gateway status'
```

Expect `active (running)`. Systemd linger is enabled by default so the gateway survives session
disconnects.

### B3 — ⛔ model credentials (human: interactive)

The agent cannot provide private API keys or interact with OAuth prompts on your behalf.

Run `matrix shell new --name auth` or launch a terminal tab from the Matrix OS web interface, then:

```bash
hermes model
```

Pick your preferred model provider (e.g. Nous free tier, OpenRouter, Anthropic, or OpenAI).
Alternatively, add your API key to `~/.hermes/.env`:

```bash
matrix run --project=main -C . -- bash -lc 'echo "OPENROUTER_API_KEY=<KEY>" >> ~/.hermes/.env'
```

Verify with a quick round-trip before proceeding:

```bash
matrix run --project=main -C . -- bash -lc 'hermes -z "Reply with the single word: alive"'
```

### B4 — clone the kit

Clone this repository into the Matrix home directory:

```bash
matrix run --project=main -C . -- \
  bash -lc 'git clone https://github.com/pridiuksson/highlander-longevity-coach.git ~/highlander-longevity-coach'

matrix run --project=main -C highlander-longevity-coach -- git rev-parse HEAD
```

Write down the commit SHA — this is the version running on your Matrix box.

### B5 — ONBOARDING steps 2–4, verbatim

Execute [ONBOARDING.md](../../ONBOARDING.md) steps 2, 3, and 4 on the Matrix computer:

1. **Backup and collision check**:
   ```bash
   matrix run --project=main -C highlander-longevity-coach -- bash -c '
   backup_dir="$HOME/.hermes/skills.bak-$(date +%Y%m%d-%H%M%S)"
   [ -d "$HOME/.hermes/skills" ] && cp -r "$HOME/.hermes/skills" "$backup_dir"
   existing=$(find -L "$HOME/.hermes/skills" -name SKILL.md -not -path "*/.archive/*" -exec grep -h "^name:" {} + | awk "{print \$2}" | sort -u)
   incoming=$(find "$HOME/highlander-longevity-coach/skills" -name SKILL.md -exec grep -h "^name:" {} + | awk "{print \$2}" | sort -u)
   comm -12 <(echo "$existing") <(echo "$incoming")
   '
   ```
   Matrix includes built-in web and UI template skills; verify that no naming collisions exist
   with the kit skills before proceeding.

2. **Install skills and restart gateway**:
   ```bash
   matrix run --project=main -C highlander-longevity-coach -- bash -lc '
   hermes gateway stop
   mkdir -p ~/.hermes/skills
   cp -r skills/* ~/.hermes/skills/
   hermes gateway restart
   hermes gateway status
   '
   ```

3. **Run gates & verify install**:
   ```bash
   # Both repo gates must pass cleanly
   matrix run --project=main -C highlander-longevity-coach -- ./scripts/leak-scan.sh .
   matrix run --project=main -C highlander-longevity-coach -- python3 scripts/validate-skills.py .

   # Verify installed skills in Hermes
   matrix run --project=main -C highlander-longevity-coach -- bash -lc \
     "python3 scripts/validate-skills.py --installed ~/.hermes"

   matrix run --project=main -C highlander-longevity-coach -- \
     bash -lc "hermes skills list | grep -E '^[0-9]+ hub-installed'"
   ```

   Expect `PASS` from `leak-scan.sh`, `OK` from `validate-skills.py`, and 25 kit skills added to the
   local skills count.

### B6 — ONBOARDING step 5, configured for Matrix

Set the skill storage paths and proactive coach settings:

```bash
matrix run --project=main -C . -- bash -lc '
hermes config set skills.config.health.health_dir ~/health
hermes config set skills.config.health.baseline_doc ~/health/baseline.md
hermes config set skills.config.proactive.timezone <TIMEZONE>
hermes config set skills.config.proactive.quiet_hours "08:00-21:00"
mkdir -p ~/health
'
```

The warning `'skills.config....' is not a recognized config key` is expected (the static schema
does not declare skill dynamic keys, but the values are persisted to `~/.hermes/config.yaml`).

### B7 — Create the Hermes Agent Desktop App & Icon (Matrix GUI)

Matrix OS desktop icons are discovered from manifests in `~/apps/<slug>/matrix.json` and placed
via the OS view state (`/api/os-view-state`). To add a dedicated **Hermes Agent** app icon to your
Matrix desktop:

1. **Deploy the desktop icon asset**:
   ```bash
   matrix run --project=main -C . -- bash -lc \
     'cp /opt/matrix/app/shell/public/agent-logos/hermes-agent.png ~/system/icons/hermes.png'
   ```

2. **Scaffold and build the Hermes app**:
   ```bash
   matrix run --project=main -C . -- bash -lc '
   cp -r ~/apps/_template-vite ~/apps/hermes
   cat << "EOF" > ~/apps/hermes/matrix.json
   {
     "name": "Hermes Agent",
     "slug": "hermes",
     "description": "Hermes AI Longevity Coach & Agent control center",
     "version": "1.0.0",
     "category": "utilities",
     "icon": "hermes",
     "author": "Matrix OS",
     "runtime": "vite",
     "runtimeVersion": "^1.0.0",
     "scope": "personal",
     "listingTrust": "first_party",
     "build": {
       "install": "pnpm install --ignore-workspace --prefer-offline",
       "command": "pnpm build",
       "output": "dist",
       "timeout": 120
     }
   }
   EOF
   cd ~/apps/hermes && npm install && npm run build
   '
   ```

3. **Pin to Desktop**:
   Add the app entry (`apps/hermes/index.html`) to the desktop icon grid via the OS-view state API
   or using the `add_app_to_desktop` tool. The icon will appear live on your Matrix desktop.

### B8 — ⛔ handback (human takes over)

The automated box setup is complete. **Do not put personal data into git or logs** — the
remaining steps are personal and interactive:

1. **Instantiate a profile** (ONBOARDING step 7):
   Select a template from `Profile/README.md`. Copy `SOUL.md` → `~/.hermes/SOUL.md`, and
   `USER.md`/`MEMORY.md` → `~/.hermes/memories/` on your Matrix box. Fill in your personal goals
   and health baselines.
2. **First run** (ONBOARDING step 8):
   Launch an interactive session via `matrix shell` or the Matrix web terminal:
   ```bash
   hermes
   ```
   Run the gate question: *"What are my hard constraints?"* — verify it answers from your profile.
3. **Wire proactive delivery** (ONBOARDING step 9):
   Run `hermes cron list` and accept the `proactive-coach` schedule (`/suggestions accept 1`).

---

## Teardown

If you want to decommission or reset the Matrix coach box:

1. **Delete local health data & skills on Matrix**:
   ```bash
   matrix run --project=main -C . -- bash -lc 'rm -rf ~/health ~/highlander-longevity-coach'
   ```
2. **Restart the instance**:
   ```bash
   matrix instance restart
   ```
3. To delete the computer completely, use the Matrix OS web console at `https://app.matrix-os.com`.

---

## Troubleshooting

| Symptom | Cause | Remedy |
|---|---|---|
| `npm install -g @finnaai/matrix` fails with `node-gyp rebuild` / `fsevents` | `fsevents` is macOS-only; npm tries building optional deps | Install in isolated prefix `~/.local/share/finnaai-matrix` with `--prefix` (A2) |
| `curl -fsSL https://get.matrix-os.com` returns 404 | Standalone install script URL moved or deprecated | Use the npm installation method (A2) |
| `matrix run` exits 1 with `Request failed` | CLI v0.3.21 bug sends `cwd: ""` which fails backend schema validation | Always specify `--project=main -C .` (e.g. `matrix run --project=main -C . -- <cmd>`) |
| `matrix run` reports file or dir not found when using `~` | Local shell expanded `~` to local home instead of remote `$HOME` | Wrap in quotes, use `bash -c '...'`, or use `$HOME` |
| `matrix run` fails with HTTP 504 `upstream unavailable` | Single command exceeded Cloudflare / gateway HTTP timeout (~30–60s) | Break long tasks into discrete commands or run them in an interactive `matrix shell` |
| `gitleaks` missing or leak-scan exits `2` | Binary not installed on the Matrix computer | Run B1 commands to download and install gitleaks 8.30.1 into `/usr/local/bin` |
| Gateway does not see new skills after copy | Skill catalogue is cached in memory | Run `hermes gateway restart` and verify with `hermes gateway status` (B5) |
| `hermes -z` fails with `not connected to any AI provider` | Model credentials missing on fresh install | Complete stop-point B3 (`hermes model` or `OPENROUTER_API_KEY` in `~/.hermes/.env`) |
