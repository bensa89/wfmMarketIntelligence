# Build Version Badge in Sidebar

**Date:** 2026-06-12  
**Status:** Approved

## Goal

Display the current deployed commit hash and build timestamp in the sidebar footer so users can quickly verify whether the running system is up to date.

## Approach

Inject build-time metadata (git commit SHA, build timestamp) as Vite environment variables during the CI Docker build. The frontend reads them statically from `import.meta.env` — no API call, no runtime overhead.

## Data Flow

```
CI (github.sha + event timestamp)
  → docker compose up --build (with env vars VITE_GIT_COMMIT, VITE_BUILD_TIME)
  → frontend Dockerfile: ARG → ENV → npm run build
  → Vite bakes values into JS bundle at build time
  → Layout.tsx VersionBadge reads import.meta.env.VITE_GIT_COMMIT / VITE_BUILD_TIME
```

## Changes

### 1. `frontend/Dockerfile`

Declare build args and expose them as ENV before `npm run build` so Vite picks them up:

```dockerfile
ARG VITE_GIT_COMMIT=dev
ARG VITE_BUILD_TIME=
ENV VITE_GIT_COMMIT=$VITE_GIT_COMMIT
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME
RUN npm run build
```

These lines go between `COPY . .` and `RUN npm run build` in the existing build stage.

### 2. `docker-compose.yml`

Add `args` to the frontend build config to pass through shell env vars:

```yaml
frontend:
  build:
    context: ./frontend
    args:
      - VITE_GIT_COMMIT
      - VITE_BUILD_TIME
```

### 3. `.github/workflows/deploy.yml`

Set both env vars in the "Deploy stack" step:

```yaml
- name: Deploy stack
  env:
    VITE_GIT_COMMIT: ${{ github.sha }}
    VITE_BUILD_TIME: ${{ github.event.head_commit.timestamp || github.event.repository.updated_at }}
  run: |
    cd /opt/wfmintel
    docker compose up -d --build
```

`github.sha` is always available. `github.event.head_commit.timestamp` is set on `push` events; `github.event.repository.updated_at` is the fallback for `workflow_dispatch` triggers.

### 4. `frontend/src/components/Layout.tsx`

Add a `VersionBadge` component rendered below the existing `LogoutButton` in the sidebar (both desktop and mobile drawer):

**Display format:**
```
──────────────────────
⬡ a1b2c3d
  12 Jun 2026 · 14:32
```

- Commit hash: first 7 chars of `VITE_GIT_COMMIT` (falls back to `"dev"` if unset)
- Timestamp: formatted from `VITE_BUILD_TIME` ISO string as `DD Mon YYYY · HH:mm` (falls back to hidden if empty)
- Icon: `GitCommit` from lucide-react (size 10), consistent with existing nav icons
- Style: `text-[10px]`, `opacity ~20%`, consistent with existing sidebar micro-text

The component is purely presentational — reads `import.meta.env.VITE_GIT_COMMIT` and `import.meta.env.VITE_BUILD_TIME` directly.

## Local Dev Behaviour

Without the env vars set, `VITE_GIT_COMMIT` defaults to `"dev"` and `VITE_BUILD_TIME` is empty. The badge shows `dev` with no timestamp — clearly distinguishable from a real deployment.

## Out of Scope

- Auto-incrementing semantic version numbers
- A dedicated `/admin/status` page
- Backend version endpoint
