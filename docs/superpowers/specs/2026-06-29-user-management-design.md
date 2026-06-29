# User Management & Login — Design Spec

**Date:** 2026-06-29  
**Status:** Approved

## Overview

Replace the current single-user HTTP Basic Auth (env-based) with a multi-user system stored in PostgreSQL. Support two roles: `admin` (full access) and `user` (read + crawls). Provide an admin UI for user management and a profile button for self-service password changes.

## 1. Data Model

New `users` table:

| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| username | varchar unique | |
| hashed_password | varchar | bcrypt |
| role | enum `admin\|user` | |
| is_active | boolean | default true |
| created_at | timestamp | |

Alembic migration required. The existing `AUTH_USERNAME` / `AUTH_PASSWORD` env settings are removed.

**Startup seed:** On app start, if `users` table is empty, create `admin` / `changeme` (bcrypt-hashed). Ensures there is always an initial login — no chicken-and-egg problem.

## 2. Backend Auth Module

New `backend/app/auth.py` replaces `verify_credentials` in `main.py`.

- `verify_credentials(credentials, db)` — looks up user by username, verifies bcrypt hash, raises 401 if invalid or inactive. Returns the `User` ORM object.
- `require_admin(user)` — raises 403 if `user.role != "admin"`. Used as a dependency on admin-only endpoints.

Global app dependency stays: `app = FastAPI(dependencies=[Depends(verify_credentials)])`.

## 3. API Endpoints

### New router: `backend/app/routers/users.py`

All under `/api/users`, admin-only except `/me` and `/me/password`:

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/me` | any | Returns `{id, username, role}` |
| PUT | `/api/me/password` | any | Change own password (requires current password) |
| GET | `/api/users` | admin | List all users |
| POST | `/api/users` | admin | Create user |
| PUT | `/api/users/{id}` | admin | Update role or active status |
| DELETE | `/api/users/{id}` | admin | Delete user |

**Safety rule:** DELETE and role downgrade fail if it would leave zero active admins.

### Role enforcement on existing endpoints

Admin-only (POST/PUT/DELETE):
- Companies, Sources, InternalCompanyContext, Settings Admin, Schedule, Digest generation, Search Candidates (approve/reject)

User + Admin:
- All GET endpoints
- `POST /api/crawl/run` and `POST /api/crawl/run/:source_id`

Implementation: existing routers get `dependencies=[Depends(require_admin)]` on write operations.

## 4. Frontend Role Awareness

**Login flow:**
1. Credentials verified via `GET /api/health` (existing)
2. On success, call `GET /api/me` and store result as `wfm_user` in `localStorage`
3. `setCredentials` stores credentials as before; new `setCurrentUser` / `clearCurrentUser` helpers manage `wfm_user`

**Hook:** `useCurrentUser()` — reads `wfm_user` from `localStorage`, returns `{username, role, isAdmin: role === "admin"}`.

**What is hidden for `role = "user"`:**
- Navigation: no Admin links (Settings, Schedule, LLM Usage, Logs, Users)
- Companies / Sources: no Add / Edit / Delete buttons
- Digests: no "Generate" button
- Search Candidates: no Approve / Reject actions
- Route guard on `/admin/users` — redirects to `/` if not admin

Crawl buttons remain visible and functional for all roles.

## 5. User Management UI

New page `UsersAdminPage` at `/admin/users`, admin-only.

**Features:**
- Table: username, role, active status, created date
- Create user: form with username, password, role
- Edit: change role via inline dropdown, toggle active/inactive
- Delete: disabled if last active admin
- Change another user's password: modal with new password + confirmation

## 6. Profile Button (Navigation)

The existing logout button in the bottom navigation is replaced by a **profile button** showing the current username. On click, a small popover appears with:

- Username + role (display only)
- "Passwort ändern" → opens a modal with: current password, new password, confirm new password. Calls `PUT /api/me/password`.
- "Abmelden" — clears credentials + `wfm_user`, redirects to `/login`

Visible to all roles.

## Out of Scope

- JWT / session tokens (HTTP Basic Auth is kept)
- Password reset via email
- OAuth / SSO
- Audit logging of user actions
