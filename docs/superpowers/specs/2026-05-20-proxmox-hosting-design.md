# Proxmox LXC Hosting + GitHub Actions Deploy — Design Spec

**Date:** 2026-05-20
**Status:** Approved

## Overview

Move the WFM Market Intelligence Hub from local development to a self-hosted Proxmox LXC container. Deployment is triggered manually via a GitHub Actions workflow that runs on a self-hosted runner inside the LXC. Secrets are managed through GitHub Secrets and Variables — never stored in the repository.

## Infrastructure: Proxmox LXC

| Parameter | Value |
|---|---|
| Base image | Debian 12 (bookworm) |
| vCPUs | 2 |
| RAM | 2 GB |
| Disk | 20 GB |
| App directory | `/opt/wfmintel` |
| App user | `wfm` (unprivileged, owns `/opt/wfmintel`) |

**Installed packages:**
- Docker Engine + Compose plugin (official Docker apt repo)
- `git`, `curl`, `ca-certificates`

**GitHub Actions Runner:**
- Installed under `/opt/wfmintel/actions-runner/`
- Registered as a repository-scoped runner (not org-level)
- Runs as `systemd` service under the `wfm` user
- Service name: `github-runner`

## Setup Script Structure

Two-phase script, modelled after Proxmox community-scripts:

### Phase 1 — `install/wfmintel-lxc.sh` (runs on Proxmox host)

1. Prompt for LXC ID, hostname, IP, gateway, storage pool
2. Download Debian 12 template if not present (`pveam download`)
3. Create LXC with `pct create` using the provided parameters
4. Start LXC, wait for boot
5. Push and execute the install script inside the LXC via `pct exec`
6. Print summary (IP, ports, next steps)

### Phase 2 — `install/wfmintel-install.sh` (runs inside LXC)

1. System update (`apt-get update && upgrade`)
2. Install Docker Engine via official apt repository
3. Create `wfm` user, add to `docker` group
4. Clone repo into `/opt/wfmintel` — uses a read-only SSH Deploy Key. Script generates an ed25519 keypair, prints the public key, and pauses asking the user to add it to GitHub (repo → Settings → Deploy keys) before continuing.
5. Create placeholder `/opt/wfmintel/.env` (populated on first deploy)
6. Download GitHub Actions runner tarball
7. Prompt for runner registration token (shown in GitHub → Settings → Actions → Runners)
8. Configure and register runner against the repository
9. Install runner as systemd service (`./svc.sh install && start`)
10. Print completion message with GitHub Actions URL

## docker-compose.yml Changes

The existing `docker-compose.yml` receives two targeted changes:

**1. `restart: unless-stopped` on all services** — ensures the stack survives LXC reboots without manual intervention.

**2. Remove exposed DB port** — delete the `ports: - "5435:5432"` mapping from the `db` service so PostgreSQL is not reachable from outside the Docker network in production.

**3. Parametrised DB credentials** — replace hardcoded `wfm:wfm` with environment variables so the GitHub Actions workflow can inject the real password:

```yaml
db:
  environment:
    POSTGRES_USER: ${POSTGRES_USER:-wfm}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-wfm}
    POSTGRES_DB: ${POSTGRES_DB:-wfmintel}
```

The `DATABASE_URL` in `.env` will be written by the workflow with the correct values.

No other changes to `docker-compose.yml` — the existing healthcheck, port mappings, and volume definitions stay as-is.

## GitHub Configuration

### Secrets (encrypted, not visible in logs)

| Secret name | Description |
|---|---|
| `AUTH_PASSWORD` | HTTP Basic Auth password |
| `DB_PASSWORD` | PostgreSQL password |
| `ANTHROPIC_API_KEY` | Claude API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `OPENCODE_API_KEY` | OpenCode API key (optional, can be empty) |

### Variables (plain text, visible in UI)

| Variable name | Example value |
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

## GitHub Actions Workflow

File: `.github/workflows/deploy.yml`
Trigger: `workflow_dispatch` (manual "Run workflow" button in GitHub UI)
Runs-on: `self-hosted`

### Steps

1. **Pull latest code** — `git -C /opt/wfmintel pull origin main`
2. **Write .env** — assembles the full `.env` file from `${{ secrets.* }}` and `${{ vars.* }}`, writes it to `/opt/wfmintel/.env`. The `DATABASE_URL` is constructed inline: `postgresql://wfm:${{ secrets.DB_PASSWORD }}@db:5432/wfmintel`.
3. **Deploy stack** — `docker compose -f /opt/wfmintel/docker-compose.yml up -d --build`
4. **Run migrations** — `docker compose -f /opt/wfmintel/docker-compose.yml exec -T backend alembic upgrade head`

The workflow does not run tests (test environment uses SQLite and runs inside Docker; tests are a separate concern for a future CI workflow).

## Network

The LXC exposes two ports:
- `80` — frontend (Nginx serving the React build)
- `8000` — backend API (FastAPI)

The existing Nginx Proxy Manager on the network handles SSL termination and domain routing. No changes needed to the app's network configuration — just point NPM to the LXC IP on port 80 (frontend) or 8000 (API) as needed.

The PostgreSQL port (`5435`) should **not** be exposed on the LXC's host network interface in the production compose file — DB access stays container-internal.

## Out of Scope

- Automated deploys on push (can be added later by changing `workflow_dispatch` to `push: branches: [main]`)
- Test CI pipeline (separate workflow, future work)
- Backup strategy (handled by Proxmox snapshot/backup at LXC level)
- Log aggregation / monitoring
