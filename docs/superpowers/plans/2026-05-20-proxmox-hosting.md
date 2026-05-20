# Proxmox LXC Hosting + GitHub Actions Deploy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the WFM Market Intelligence Hub on a Proxmox LXC via a self-hosted GitHub Actions runner with manual workflow_dispatch deploys.

**Architecture:** A two-phase bash setup script creates a Debian 12 LXC on the Proxmox host, installs Docker and the GitHub Actions runner inside it, and clones the repo via SSH deploy key. A `workflow_dispatch` GitHub Actions workflow then handles all future deploys: it pulls code, writes `.env` from GitHub Secrets/Variables, builds Docker images locally, and runs Alembic migrations.

**Tech Stack:** Bash, Proxmox `pct`, Docker Compose v2, GitHub Actions, Alembic, shellcheck (linting)

---

## File Map

| Action | Path |
|---|---|
| Modify | `docker-compose.yml` |
| Create | `.github/workflows/deploy.yml` |
| Create | `install/wfmintel-install.sh` |
| Create | `install/wfmintel-lxc.sh` |
| Create (once) | `install/seed.dump` *(binary, not tracked by git LFS — private repo only)* |

> **Task order:** Complete Task 7 (seed dump) first, then push to GitHub, then run Tasks 3–4 on the Proxmox host. Tasks 1–2 can be done at any point before the first deploy.

---

## Task 1: Harden docker-compose.yml for production

**Files:**
- Modify: `docker-compose.yml`

Three targeted changes: add `restart: unless-stopped` to every service, remove the exposed DB port, and parametrize PostgreSQL credentials so the GitHub Actions workflow can inject them via `.env`.

- [ ] **Step 1: Open docker-compose.yml and apply changes**

Replace the entire file content with:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-wfm}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-wfm}
      POSTGRES_DB: ${POSTGRES_DB:-wfmintel}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-wfm}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

Note: `5435:5432` is intentionally removed — PostgreSQL is only accessible inside the Docker network in production. The dev compose (`docker-compose.dev.yml`) retains the port mapping unchanged.

- [ ] **Step 2: Verify the compose file is valid**

```bash
docker compose -f docker-compose.yml config --quiet
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: harden production compose (restart policy, remove DB port, parametrize creds)"
```

---

## Task 2: Create GitHub Actions deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

Manual `workflow_dispatch` trigger. The workflow runs on the self-hosted runner inside the LXC. Secrets are passed as environment variables to the shell step (never interpolated directly into run scripts) to avoid issues with special characters in secret values.

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create .github/workflows/deploy.yml**

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      branch:
        description: 'Branch to deploy'
        required: true
        default: 'main'

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - name: Pull latest code
        run: git -C /opt/wfmintel pull origin ${{ github.event.inputs.branch }}

      - name: Write .env
        env:
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          AUTH_PASSWORD: ${{ secrets.AUTH_PASSWORD }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}
        run: |
          {
            echo "DATABASE_URL=postgresql://wfm:${DB_PASSWORD}@db:5432/wfmintel"
            echo "POSTGRES_USER=wfm"
            echo "POSTGRES_PASSWORD=${DB_PASSWORD}"
            echo "POSTGRES_DB=wfmintel"
            echo "AUTH_USERNAME=${{ vars.AUTH_USERNAME }}"
            echo "AUTH_PASSWORD=${AUTH_PASSWORD}"
            echo "LLM_PROVIDER=${{ vars.LLM_PROVIDER }}"
            echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
            echo "CLAUDE_MODEL=${{ vars.CLAUDE_MODEL }}"
            echo "OLLAMA_BASE_URL=${{ vars.OLLAMA_BASE_URL }}"
            echo "OLLAMA_MODEL=${{ vars.OLLAMA_MODEL }}"
            echo "OPENCODE_API_KEY=${OPENCODE_API_KEY}"
            echo "OPENCODE_BASE_URL=${{ vars.OPENCODE_BASE_URL }}"
            echo "OPENCODE_MODEL=${{ vars.OPENCODE_MODEL }}"
            echo "DISCOVERY_DEPTH=${{ vars.DISCOVERY_DEPTH }}"
            echo "JS_RENDERING_ENABLED=${{ vars.JS_RENDERING_ENABLED }}"
            echo "CRAWL_CONCURRENCY=${{ vars.CRAWL_CONCURRENCY }}"
            echo "DISCOVERY_CONCURRENCY=${{ vars.DISCOVERY_CONCURRENCY }}"
            echo "ANALYSIS_CONCURRENCY=${{ vars.ANALYSIS_CONCURRENCY }}"
            echo "SEARCH_RELEVANCE_THRESHOLD=${{ vars.SEARCH_RELEVANCE_THRESHOLD }}"
            echo "SEARCH_QUERIES_PER_COMPANY=${{ vars.SEARCH_QUERIES_PER_COMPANY }}"
            echo "ASSESSMENT_THRESHOLD=${{ vars.ASSESSMENT_THRESHOLD }}"
            echo "TAVILY_API_KEY=${TAVILY_API_KEY}"
          } > /opt/wfmintel/.env

      - name: Deploy stack
        run: |
          cd /opt/wfmintel
          docker compose up -d --build

      - name: Run migrations
        run: |
          docker compose -f /opt/wfmintel/docker-compose.yml exec -T backend alembic upgrade head
```

- [ ] **Step 3: Lint the workflow YAML**

```bash
# Install actionlint if not present
brew install actionlint 2>/dev/null || true
actionlint .github/workflows/deploy.yml
```

Expected: no errors. If `actionlint` is not available, visually verify indentation and that all `${{ }}` expressions are syntactically correct.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: add manual deploy workflow for self-hosted runner"
```

---

## Task 3: Create LXC install script (Phase 2 — runs inside LXC)

**Files:**
- Create: `install/wfmintel-install.sh`

This script runs inside a fresh Debian 12 LXC as root. It installs Docker, creates the `wfm` user, generates an SSH deploy key (pausing for the user to add it to GitHub), clones the repo, and sets up the GitHub Actions runner as a systemd service.

- [ ] **Step 1: Create the install directory**

```bash
mkdir -p install
```

- [ ] **Step 2: Create install/wfmintel-install.sh**

```bash
#!/bin/bash
set -euo pipefail

APP_DIR="/opt/wfmintel"
APP_USER="wfm"
RUNNER_DIR="${APP_DIR}/actions-runner"
REPO_SSH="git@github.com:bensa89/wfmMarketIntelligence.git"
REPO_HTTPS="https://github.com/bensa89/wfmMarketIntelligence"

msg() { echo -e "\n\033[1;34m>>> $*\033[0m"; }
ok()  { echo -e "\033[1;32m    ✓ $*\033[0m"; }

msg "Updating system packages"
apt-get update -qq && apt-get upgrade -y -qq

msg "Installing prerequisites"
apt-get install -y -qq curl ca-certificates git openssh-client

msg "Installing Docker Engine"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

msg "Creating app user '${APP_USER}'"
useradd -m -s /bin/bash "$APP_USER" || true
usermod -aG docker "$APP_USER"
ok "User ${APP_USER} created and added to docker group"

msg "Generating SSH deploy key"
SSH_DIR="/home/${APP_USER}/.ssh"
mkdir -p "$SSH_DIR"
sudo -u "$APP_USER" ssh-keygen -t ed25519 -f "${SSH_DIR}/deploy_key" -N "" -C "wfmintel-deploy" -q
cat > "${SSH_DIR}/config" << 'EOF'
Host github.com
    IdentityFile ~/.ssh/deploy_key
    StrictHostKeyChecking accept-new
EOF
chown -R "${APP_USER}:${APP_USER}" "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "${SSH_DIR}/deploy_key" "${SSH_DIR}/config"

echo ""
echo "========================================================"
echo "  Add this deploy key to GitHub before continuing:"
echo "  ${REPO_HTTPS}/settings/keys/new"
echo "  Title: wfmintel-proxmox | Allow write access: NO"
echo "========================================================"
cat "${SSH_DIR}/deploy_key.pub"
echo "========================================================"
read -rp "Press ENTER once the deploy key has been added..."

msg "Cloning repository"
mkdir -p "$(dirname "$APP_DIR")"
sudo -u "$APP_USER" git clone "$REPO_SSH" "$APP_DIR"
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR"
ok "Repository cloned to ${APP_DIR}"

msg "Creating placeholder .env"
cat > "${APP_DIR}/.env" << 'EOF'
# Written by GitHub Actions on each deploy. Do not edit manually.
EOF
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

msg "Downloading GitHub Actions runner"
mkdir -p "$RUNNER_DIR"
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest \
  | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
curl -fsSL \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
  | tar -xz -C "$RUNNER_DIR"
chown -R "${APP_USER}:${APP_USER}" "$RUNNER_DIR"
ok "Runner v${RUNNER_VERSION} downloaded"

echo ""
echo "========================================================"
echo "  Get your runner token from GitHub:"
echo "  ${REPO_HTTPS}/settings/actions/runners/new?runnerOs=linux"
echo "========================================================"
read -rp "Runner registration token: " RUNNER_TOKEN

msg "Configuring GitHub Actions runner"
sudo -u "$APP_USER" bash -c \
  "cd '${RUNNER_DIR}' && ./config.sh \
    --url '${REPO_HTTPS}' \
    --token '${RUNNER_TOKEN}' \
    --name 'proxmox-lxc' \
    --labels 'self-hosted,linux' \
    --unattended"

msg "Installing runner as systemd service"
cd "$RUNNER_DIR"
./svc.sh install "$APP_USER"
./svc.sh start

msg "Checking for seed database"
SEED_FILE="${APP_DIR}/install/seed.dump"
if [[ -f "$SEED_FILE" ]]; then
    msg "Seed file found — restoring initial data"

    # Minimal .env to start the db container only
    cat > "${APP_DIR}/.env" << 'EOF'
POSTGRES_USER=wfm
POSTGRES_PASSWORD=wfm
POSTGRES_DB=wfmintel
DATABASE_URL=postgresql://wfm:wfm@db:5432/wfmintel
EOF
    chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

    cd "$APP_DIR"
    sudo -u "$APP_USER" docker compose up -d db

    echo "    Waiting for database to be ready..."
    for i in $(seq 1 30); do
        if sudo -u "$APP_USER" docker compose exec -T db pg_isready -U wfm -q 2>/dev/null; then
            break
        fi
        sleep 2
    done

    sudo -u "$APP_USER" docker compose cp "$SEED_FILE" db:/tmp/seed.dump
    sudo -u "$APP_USER" docker compose exec -T db \
        pg_restore -U wfm -d wfmintel --no-owner --clean --if-exists /tmp/seed.dump

    sudo -u "$APP_USER" docker compose down
    ok "Seed data restored — .env will be overwritten on first GitHub Actions deploy"
else
    ok "No seed file found — stack will start with an empty database"
fi

LXC_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "========================================================"
echo "  Installation complete!"
echo "  Frontend : http://${LXC_IP}:80"
echo "  API      : http://${LXC_IP}:8000"
echo ""
echo "  Trigger first deploy from GitHub Actions to start the"
echo "  full stack and set real credentials via .env."
echo "========================================================"
```

- [ ] **Step 3: Make script executable**

```bash
chmod +x install/wfmintel-install.sh
```

- [ ] **Step 4: Lint with shellcheck**

```bash
shellcheck install/wfmintel-install.sh
```

Expected: no errors or warnings. Install shellcheck if needed: `brew install shellcheck`.

- [ ] **Step 5: Commit**

```bash
git add install/wfmintel-install.sh
git commit -m "feat: add LXC install script (phase 2)"
```

---

## Task 4: Create Proxmox LXC creation script (Phase 1 — runs on Proxmox host)

**Files:**
- Create: `install/wfmintel-lxc.sh`

This script runs on the Proxmox host (not inside a container). It downloads the Debian 12 template if missing, creates the LXC with the right parameters (unprivileged, Docker-capable via `nesting=1`), and then executes the Phase 2 install script inside the new container.

- [ ] **Step 1: Verify the correct Debian 12 template name on your Proxmox host**

Run on the Proxmox host:
```bash
pveam available --section system | grep debian-12
```

Note the exact filename (e.g. `debian-12-standard_12.7-1_amd64.tar.zst`). Update the `TEMPLATE` variable in the script below if it differs.

- [ ] **Step 2: Create install/wfmintel-lxc.sh**

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

msg() { echo -e "\n\033[1;34m>>> $*\033[0m"; }

# --- Configuration ---
CT_ID=${1:-200}
CT_HOSTNAME="wfmintel"
CT_CORES=2
CT_RAM=2048
CT_DISK=20
CT_STORAGE="local-lvm"
CT_BRIDGE="vmbr0"
TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"
TEMPLATE_STORAGE="local"

echo "========================================================"
echo "  WFM Market Intelligence — Proxmox LXC Setup"
echo "  LXC ID: ${CT_ID}  |  Hostname: ${CT_HOSTNAME}"
echo "========================================================"

read -rp "LXC IP with CIDR (e.g. 192.168.1.50/24): " CT_IP
read -rp "Default gateway (e.g. 192.168.1.1):        " CT_GW
read -rp "Storage pool [${CT_STORAGE}]:               " CT_STORAGE_IN
CT_STORAGE="${CT_STORAGE_IN:-$CT_STORAGE}"

msg "Checking for Debian 12 template"
if ! pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -q "$TEMPLATE"; then
    msg "Downloading Debian 12 template (this may take a moment)..."
    pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
fi
echo "    ✓ Template ready"

msg "Creating LXC ${CT_ID}"
pct create "$CT_ID" "${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE}" \
    --hostname "$CT_HOSTNAME" \
    --cores "$CT_CORES" \
    --memory "$CT_RAM" \
    --rootfs "${CT_STORAGE}:${CT_DISK}" \
    --net0 "name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP},gw=${CT_GW}" \
    --unprivileged 1 \
    --features "nesting=1" \
    --onboot 1

msg "Starting LXC"
pct start "$CT_ID"

msg "Waiting for LXC to boot (10s)"
sleep 10

msg "Copying install script into LXC"
pct push "$CT_ID" "${SCRIPT_DIR}/wfmintel-install.sh" /root/wfmintel-install.sh
pct exec "$CT_ID" -- chmod +x /root/wfmintel-install.sh

msg "Running install script inside LXC"
pct exec "$CT_ID" -- bash /root/wfmintel-install.sh

echo ""
echo "========================================================"
echo "  LXC ${CT_ID} (${CT_HOSTNAME}) setup complete."
echo "  IP: ${CT_IP%/*}"
echo "  Run 'pct enter ${CT_ID}' to open a shell."
echo "========================================================"
```

- [ ] **Step 3: Make script executable**

```bash
chmod +x install/wfmintel-lxc.sh
```

- [ ] **Step 4: Lint with shellcheck**

```bash
shellcheck install/wfmintel-lxc.sh
```

Expected: no errors or warnings.

- [ ] **Step 5: Commit**

```bash
git add install/wfmintel-lxc.sh
git commit -m "feat: add Proxmox LXC creation script (phase 1)"
```

---

## Task 5: Configure GitHub Secrets and Variables

This task is performed in the GitHub UI — not in code. It must be completed before the first deploy workflow run.

- [ ] **Step 1: Open repository settings**

Navigate to: `https://github.com/bensa89/wfmMarketIntelligence/settings/secrets/actions`

- [ ] **Step 2: Create Secrets** (Settings → Secrets and variables → Actions → Secrets)

| Name | Value |
|---|---|
| `AUTH_PASSWORD` | The HTTP Basic Auth password for the app |
| `DB_PASSWORD` | PostgreSQL password (choose a strong password) |
| `ANTHROPIC_API_KEY` | Your `sk-ant-...` key |
| `TAVILY_API_KEY` | Your `tvly-...` key |
| `OPENCODE_API_KEY` | Your OpenCode key (or leave empty string if unused) |

- [ ] **Step 3: Create Variables** (Settings → Secrets and variables → Actions → Variables)

| Name | Value |
|---|---|
| `AUTH_USERNAME` | `admin` |
| `LLM_PROVIDER` | `claude` |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3` |
| `OPENCODE_BASE_URL` | `https://opencode.ai/zen/go/v1` |
| `OPENCODE_MODEL` | `qwen3.6-plus` |
| `DISCOVERY_DEPTH` | `1` |
| `JS_RENDERING_ENABLED` | `true` |
| `CRAWL_CONCURRENCY` | `4` |
| `DISCOVERY_CONCURRENCY` | `3` |
| `ANALYSIS_CONCURRENCY` | `3` |
| `SEARCH_RELEVANCE_THRESHOLD` | `0.5` |
| `SEARCH_QUERIES_PER_COMPANY` | `8` |
| `ASSESSMENT_THRESHOLD` | `0.4` |

---

## Task 6: First deploy and verification

Prerequisites: LXC is running, runner is registered and online in GitHub, Secrets/Variables are configured.

- [ ] **Step 1: Verify runner is online**

In GitHub: `https://github.com/bensa89/wfmMarketIntelligence/settings/actions/runners`

Expected: runner `proxmox-lxc` shows status **Idle**.

- [ ] **Step 2: Trigger first deploy**

In GitHub: Actions → Deploy → Run workflow → branch: `main` → Run workflow.

- [ ] **Step 3: Watch workflow logs**

Monitor the run. Expected sequence:
1. `Pull latest code` — succeeds, shows commit hash
2. `Write .env` — succeeds silently (secrets are masked in logs)
3. `Deploy stack` — Docker builds images (first run takes several minutes), then `Started` for all 3 services
4. `Run migrations` — Alembic output ends with `Running upgrade ... -> ...`

- [ ] **Step 4: Verify the app is reachable**

```bash
curl -u admin:<AUTH_PASSWORD> http://<LXC_IP>:8000/api/companies
```

Expected: `[]` (empty list) or existing data. HTTP 200.

Open `http://<LXC_IP>:80` in a browser — the React frontend should load.

- [ ] **Step 5: Verify restart survives reboot**

```bash
# On Proxmox host
pct reboot <CT_ID>
# Wait ~30 seconds, then:
curl -u admin:<AUTH_PASSWORD> http://<LXC_IP>:8000/api/companies
```

Expected: HTTP 200 — containers came back up automatically via `restart: unless-stopped`.

---

---

## Task 7: Create and commit database seed *(run BEFORE Tasks 3–4)*

The seed dump is committed to `install/seed.dump` in the repo. The install script (Task 3) detects the file automatically and restores it during LXC setup — no manual file transfer needed.

> **Note:** This commits competitor intelligence data to the git repo. Only do this if the repo is private (`bensa89/wfmMarketIntelligence` is private — verified via SSH remote).

- [ ] **Step 1: Ensure the local dev stack is running**

```bash
docker compose -f docker-compose.dev.yml up -d
```

Expected: all three containers are `Up`.

- [ ] **Step 2: Create the seed dump**

```bash
docker compose -f docker-compose.dev.yml exec db \
  pg_dump -U wfm -Fc wfmintel > install/seed.dump
```

Verify it is non-empty:

```bash
ls -lh install/seed.dump
```

Expected: file size > 0 bytes (typically a few MB depending on how much data is collected).

- [ ] **Step 3: Commit the seed**

```bash
git add install/seed.dump
git commit -m "chore: add initial database seed for LXC deployment"
```

- [ ] **Step 4: Push to GitHub**

```bash
git push origin main
```

The install script (Task 3) will clone the repo including this file and restore it automatically during LXC setup.

---

## Notes for Nginx Proxy Manager

After confirming the app runs on the LXC IP, add two proxy hosts in NPM:

- `wfm.yourdomain.com` → `http://<LXC_IP>:80` (frontend)
- `wfm-api.yourdomain.com` → `http://<LXC_IP>:8000` (API, if needed externally)

SSL and certs are handled by NPM — no changes needed in the app.
