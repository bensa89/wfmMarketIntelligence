# User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace single-credential HTTP Basic Auth with a DB-backed multi-user system supporting `admin` and `user` roles, with a frontend admin UI for user management and a profile popover for self-service password changes.

**Architecture:** New `User` model in PostgreSQL with bcrypt-hashed passwords. A new `app/auth.py` module replaces the current single-credential check in `main.py` and exposes `verify_credentials` (global dep) and `require_admin` (admin-only dep). The frontend fetches `/api/me` after login, stores the role in `localStorage`, and uses a `useCurrentUser()` hook to conditionally render admin-only UI.

**Tech Stack:** Python/FastAPI, SQLAlchemy 2.0, Alembic, bcrypt (`passlib[bcrypt]`), React 18 + TypeScript, React Query, Lucide icons.

## Global Constraints

- Tests run inside Docker: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v`
- HTTP Basic Auth stays (no JWT)
- `passlib[bcrypt]` for password hashing (already common in FastAPI ecosystem)
- All existing tests must continue to pass after each task
- Frontend: no new dependencies, use existing Lucide icons

---

## File Map

**Backend — New:**
- `backend/app/models/user.py` — User ORM model (username, hashed_password, role, is_active)
- `backend/app/schemas/user.py` — Pydantic schemas: UserRead, UserCreate, UserUpdate, PasswordChange
- `backend/app/auth.py` — `verify_credentials`, `require_admin`, `get_current_user`
- `backend/app/routers/users.py` — `/api/me`, `/api/me/password`, `/api/users` CRUD
- `backend/tests/test_users.py` — tests for users router

**Backend — Modified:**
- `backend/app/models/__init__.py` — add User import
- `backend/app/main.py` — use auth.py, startup seed, register users router
- `backend/app/config.py` — remove `auth_username`, `auth_password`
- `backend/tests/conftest.py` — seed test user, add `user_client` fixture, remove old env vars

**Existing routers — Modified (require_admin on write ops):**
- `backend/app/routers/companies.py`
- `backend/app/routers/sources.py`
- `backend/app/routers/context.py`
- `backend/app/routers/digests.py`
- `backend/app/routers/search.py`
- `backend/app/routers/schedule.py`
- `backend/app/routers/settings_admin.py`

**Frontend — New:**
- `frontend/src/hooks/useCurrentUser.ts` — reads `wfm_user` from localStorage
- `frontend/src/components/ProfilePopover.tsx` — popover with change-password modal
- `frontend/src/pages/UsersAdminPage.tsx` — user management UI

**Frontend — Modified:**
- `frontend/src/api/client.ts` — add `setCurrentUser`, `clearCurrentUser`, `getCurrentUser`
- `frontend/src/pages/LoginPage.tsx` — call `/api/me` after login, store user
- `frontend/src/components/Layout.tsx` — replace LogoutButton with ProfileButton, filter admin nav
- `frontend/src/App.tsx` — add `/admin/users` route with admin guard

**Pages — Modified (hide write actions for non-admin):**
- `frontend/src/pages/WeeklyDigestPage.tsx` — hide "Generate New Digest" button
- `frontend/src/pages/SearchPage.tsx` — hide Approve/Reject buttons

---

## Task 1: User model + Pydantic schemas + Alembic migration

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/schemas/user.py`
- Modify: `backend/app/models/__init__.py`
- Run: Alembic migration

**Interfaces:**
- Produces: `User` ORM class with fields `id, username, hashed_password, role, is_active, created_at`; `UserRole` enum with values `"admin"` and `"user"`

- [ ] **Step 1: Install passlib**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend pip install "passlib[bcrypt]"
```

Add to `backend/requirements.txt` (find the existing file and append):
```
passlib[bcrypt]
```

- [ ] **Step 2: Create `backend/app/models/user.py`**

```python
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: Create `backend/app/schemas/user.py`**

```python
from pydantic import BaseModel
from datetime import datetime
from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.user


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class MeResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    username: str
    role: UserRole
```

- [ ] **Step 4: Register User in `backend/app/models/__init__.py`**

Add at the top of the import block:
```python
from app.models.user import User, UserRole  # noqa: F401
```

Add `"User"` and `"UserRole"` to `__all__`.

- [ ] **Step 5: Generate and apply Alembic migration**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add users table"
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend alembic upgrade head
```

Verify output shows `add users table` upgrade with no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user.py backend/app/schemas/user.py backend/app/models/__init__.py backend/requirements.txt backend/alembic/versions/
git commit -m "feat: add User model and schemas"
```

---

## Task 2: Auth module + main.py wiring + conftest update

**Files:**
- Create: `backend/app/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `User` from `backend/app/models/user.py`, `UserRole`
- Produces:
  - `verify_credentials(credentials: HTTPBasicCredentials, db: Session) -> User` — global FastAPI dep
  - `get_current_user` — alias for `verify_credentials`, returns `User`
  - `require_admin(user: User = Depends(get_current_user)) -> User` — raises 403 if not admin

- [ ] **Step 1: Write failing test for auth module**

Create `backend/tests/test_auth.py`:

```python
import base64
from fastapi.testclient import TestClient


def _basic(username: str, password: str) -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()}


def test_valid_admin_credentials(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_invalid_credentials_rejected(db_session):
    from app.main import app
    from app.database import get_db

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app, headers=_basic("wrong", "wrong")) as c:
        resp = c.get("/api/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_inactive_user_rejected(db_session):
    from app.main import app
    from app.database import get_db
    from app.models.user import User

    user = db_session.query(User).filter_by(username="testuser").first()
    user.is_active = False
    db_session.commit()

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app, headers=_basic("testuser", "testpass")) as c:
        resp = c.get("/api/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 401
```

Run: `docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_auth.py -v`

Expected: FAIL (auth module not yet created)

- [ ] **Step 2: Create `backend/app/auth.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.database import get_db
from app.models.user import User, UserRole

security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account deactivated",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


get_current_user = verify_credentials


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

- [ ] **Step 3: Update `backend/app/config.py`**

Remove `auth_username` and `auth_password` fields. The file becomes:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True)

    database_url: str = "postgresql://wfm:wfm@localhost:5432/wfmintel"
    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    opencode_api_key: str = ""
    opencode_base_url: str = "https://opencode.ai/zen/go/v1"
    opencode_model: str = "qwen3.6-plus"
    discovery_depth: int = 1
    js_rendering_enabled: bool = True
    tavily_api_key: str = ""
    search_relevance_threshold: float = 0.5
    search_queries_per_company: int = 8
    assessment_threshold: float = 0.4
    crawl_concurrency: int = 4
    discovery_concurrency: int = 3
    analysis_concurrency: int = 3
    app_base_url: str = "https://wfm.saure.me"


settings = Settings()
```

- [ ] **Step 4: Update `backend/app/main.py`**

Replace the existing `security`, `verify_credentials` definitions and `from app.config import settings` auth usage. The updated top of `main.py`:

```python
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth import verify_credentials, hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger(__name__)
```

Add a startup seed function (insert before `lifespan`):

```python
def _seed_initial_admin():
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                username="admin",
                hashed_password=hash_password("changeme"),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Seeded initial admin user (admin/changeme)")
    finally:
        db.close()
```

Call `_seed_initial_admin()` inside `lifespan`, right after `log_stream.install()`:

```python
    log_stream.install()
    _seed_initial_admin()
```

Change the `app` declaration to use `auth.verify_credentials`:

```python
app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
    lifespan=lifespan,
)
```

Remove the old `from fastapi.security import HTTPBasic, HTTPBasicCredentials` and `import secrets` imports.

- [ ] **Step 5: Update `backend/tests/conftest.py`**

Replace the entire file:

```python
import base64
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
import app.models  # noqa: F401

TEST_DB_PATH = "./test_app.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(b"testuser:testpass").decode()
}
USER_AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(b"regularuser:userpass").decode()
}


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    import app.database as database_module
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    original_session_local = database_module.SessionLocal
    database_module.SessionLocal = test_session_factory

    yield engine

    database_module.SessionLocal = original_session_local
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def db_session(db_engine):
    from app.models.user import User, UserRole
    from app.auth import hash_password

    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()

    admin = User(username="testuser", hashed_password=hash_password("testpass"), role=UserRole.admin, is_active=True)
    regular = User(username="regularuser", hashed_password=hash_password("userpass"), role=UserRole.user, is_active=True)
    session.add_all([admin, regular])
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.scheduler.startup_scheduler", lambda engine: None), \
         patch("app.scheduler.shutdown_scheduler", lambda: None), \
         patch("app.scheduler.apply_schedule", lambda config: None):
        with TestClient(app, headers=AUTH_HEADER) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_client(db_session):
    """TestClient authenticated as a regular (non-admin) user."""
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.scheduler.startup_scheduler", lambda engine: None), \
         patch("app.scheduler.shutdown_scheduler", lambda: None), \
         patch("app.scheduler.apply_schedule", lambda config: None):
        with TestClient(app, headers=USER_AUTH_HEADER) as c:
            yield c

    app.dependency_overrides.clear()
```

- [ ] **Step 6: Run tests**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_auth.py tests/test_companies.py -v
```

Expected: all PASS (test_auth tests now pass, existing tests unaffected)

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth.py backend/app/config.py backend/app/main.py backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "feat: replace single-credential auth with DB-backed user auth"
```

---

## Task 3: Users router

**Files:**
- Create: `backend/app/routers/users.py`
- Create: `backend/tests/test_users.py`
- Modify: `backend/app/main.py` — register router

**Interfaces:**
- Consumes: `verify_credentials`, `require_admin`, `get_current_user` from `app.auth`; `User` ORM; schemas from `app.schemas.user`
- Produces: endpoints `/api/me` (GET), `/api/me/password` (PUT), `/api/users` (GET, POST), `/api/users/{id}` (PUT, DELETE)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_users.py`:

```python
def test_me_returns_current_user(client):
    resp = client.get("/api/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["role"] == "admin"


def test_list_users_admin_only(client, user_client):
    assert client.get("/api/users").status_code == 200
    assert user_client.get("/api/users").status_code == 403


def test_create_user(client):
    payload = {"username": "newuser", "password": "secret123", "role": "user"}
    resp = client.post("/api/users", json=payload)
    assert resp.status_code == 201
    assert resp.json()["username"] == "newuser"


def test_create_duplicate_username_fails(client):
    client.post("/api/users", json={"username": "dup", "password": "x", "role": "user"})
    resp = client.post("/api/users", json={"username": "dup", "password": "y", "role": "user"})
    assert resp.status_code == 409


def test_create_user_requires_admin(user_client):
    resp = user_client.post("/api/users", json={"username": "x", "password": "y", "role": "user"})
    assert resp.status_code == 403


def test_update_user_role(client):
    create = client.post("/api/users", json={"username": "tochange", "password": "pw", "role": "user"})
    uid = create.json()["id"]
    resp = client.put(f"/api/users/{uid}", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_delete_last_admin_blocked(client, db_session):
    from app.models.user import User
    admin = db_session.query(User).filter_by(username="testuser").first()
    resp = client.delete(f"/api/users/{admin.id}")
    assert resp.status_code == 409


def test_delete_user(client):
    create = client.post("/api/users", json={"username": "todelete", "password": "pw", "role": "user"})
    uid = create.json()["id"]
    assert client.delete(f"/api/users/{uid}").status_code == 204


def test_change_own_password(client):
    resp = client.put("/api/users/me/password", json={"current_password": "testpass", "new_password": "newpass"})
    assert resp.status_code == 200


def test_change_own_password_wrong_current(client):
    resp = client.put("/api/users/me/password", json={"current_password": "wrong", "new_password": "new"})
    assert resp.status_code == 400
```

Run: `docker compose ... exec backend python -m pytest tests/test_users.py -v`
Expected: FAIL (router not yet created)

- [ ] **Step 2: Create `backend/app/routers/users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_user, require_admin, hash_password, pwd_context
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserCreate, UserUpdate, PasswordChange, MeResponse

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password", response_model=MeResponse)
def change_own_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not pwd_context.verify(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=List[UserRead], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    active_admins = db.query(User).filter(User.role == UserRole.admin, User.is_active == True).count()
    if user.role == UserRole.admin and active_admins <= 1:
        raise HTTPException(status_code=409, detail="Cannot delete the last active admin")
    db.delete(user)
    db.commit()
```

- [ ] **Step 3: Register router in `backend/app/main.py`**

Add import and `include_router` call:

```python
from app.routers import users
# ...
app.include_router(users.router, prefix="/api/users", tags=["users"])
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/test_users.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/users.py backend/tests/test_users.py backend/app/main.py
git commit -m "feat: add users router with CRUD and /api/me endpoints"
```

---

## Task 4: Role enforcement on existing routers

**Files:**
- Modify: `backend/app/routers/companies.py`
- Modify: `backend/app/routers/sources.py`
- Modify: `backend/app/routers/context.py`
- Modify: `backend/app/routers/digests.py`
- Modify: `backend/app/routers/search.py`
- Modify: `backend/app/routers/schedule.py`
- Modify: `backend/app/routers/settings_admin.py`
- Create: `backend/tests/test_role_enforcement.py`

**Interfaces:**
- Consumes: `require_admin` from `app.auth`
- Produces: 403 responses for non-admin users on write endpoints

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_role_enforcement.py`:

```python
def test_user_cannot_create_company(user_client):
    resp = user_client.post("/api/companies", json={"name": "X", "slug": "x", "type": "competitor"})
    assert resp.status_code == 403


def test_user_can_list_companies(user_client):
    assert user_client.get("/api/companies").status_code == 200


def test_user_cannot_create_source(user_client, client):
    client.post("/api/companies", json={"name": "C", "slug": "c-role", "type": "competitor"})
    company = client.get("/api/companies/c-role").json()
    resp = user_client.post("/api/sources", json={
        "url": "https://example.com",
        "type": "blog",
        "company_id": company["id"],
    })
    assert resp.status_code == 403


def test_user_cannot_update_context(user_client):
    resp = user_client.put("/api/context", json={"target_industries": ["HR"]})
    assert resp.status_code == 403


def test_user_cannot_generate_digest(user_client):
    resp = user_client.post("/api/digests/generate")
    assert resp.status_code == 403


def test_user_can_list_digests(user_client):
    assert user_client.get("/api/digests").status_code == 200


def test_user_cannot_update_schedule(user_client):
    resp = user_client.put("/api/schedule", json={"enabled": False})
    assert resp.status_code == 403


def test_user_cannot_update_settings(user_client):
    resp = user_client.put("/api/admin/settings/some_key", json={"value": "x"})
    assert resp.status_code in (403, 404)
```

Run: `docker compose ... exec backend python -m pytest tests/test_role_enforcement.py -v`
Expected: FAIL

- [ ] **Step 2: Add `require_admin` to `companies.py`**

Add import at top: `from app.auth import require_admin`

Add `dependencies=[Depends(require_admin)]` to write endpoints:

```python
@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_company(...):
    ...

@router.put("/{slug}", response_model=CompanyRead, dependencies=[Depends(require_admin)])
def update_company(...):
    ...

@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_company(...):
    ...

@router.post("/{slug}/logo", response_model=CompanyRead, dependencies=[Depends(require_admin)])
async def upload_logo(...):
    ...
```

GET endpoints stay unchanged.

- [ ] **Step 3: Add `require_admin` to `sources.py`**

Add import: `from app.auth import require_admin`

Add `dependencies=[Depends(require_admin)]` to all POST, PUT, DELETE endpoints in `sources.py`. GET endpoints stay unchanged.

- [ ] **Step 4: Add `require_admin` to `context.py`**

Add import: `from app.auth import require_admin`

Add `dependencies=[Depends(require_admin)]` to the PUT endpoint (the one that updates context). GET stays unchanged.

- [ ] **Step 5: Add `require_admin` to `digests.py`**

Add import: `from app.auth import require_admin`

Find the `POST /generate` endpoint and add `dependencies=[Depends(require_admin)]`. GET endpoints stay unchanged.

- [ ] **Step 6: Add `require_admin` to `search.py` candidates**

Add import: `from app.auth import require_admin`

Find the approve and reject POST endpoints on the candidates router and add `dependencies=[Depends(require_admin)]`.

- [ ] **Step 7: Add `require_admin` to `schedule.py`**

Add import: `from app.auth import require_admin`

Add `dependencies=[Depends(require_admin)]` to all write endpoints (PUT/POST). GET stays unchanged.

- [ ] **Step 8: Add `require_admin` to `settings_admin.py`**

Add import: `from app.auth import require_admin`

Add `dependencies=[Depends(require_admin)]` to all endpoints in this router (all are write operations).

- [ ] **Step 9: Run all tests**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/routers/companies.py backend/app/routers/sources.py backend/app/routers/context.py backend/app/routers/digests.py backend/app/routers/search.py backend/app/routers/schedule.py backend/app/routers/settings_admin.py backend/tests/test_role_enforcement.py
git commit -m "feat: enforce admin role on write endpoints"
```

---

## Task 5: Frontend auth foundations

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/hooks/useCurrentUser.ts`
- Modify: `frontend/src/pages/LoginPage.tsx`

**Interfaces:**
- Produces:
  - `setCurrentUser(user: CurrentUser): void`
  - `clearCurrentUser(): void`
  - `getCurrentUser(): CurrentUser | null`
  - `useCurrentUser(): { username: string; role: 'admin' | 'user'; isAdmin: boolean } | null`
  - `CurrentUser` type: `{ id: number; username: string; role: 'admin' | 'user' }`

- [ ] **Step 1: Add user helpers to `frontend/src/api/client.ts`**

Add this type and three functions after the existing `clearCredentials` function:

```typescript
export interface CurrentUser {
  id: number;
  username: string;
  role: 'admin' | 'user';
}

export function setCurrentUser(user: CurrentUser): void {
  localStorage.setItem('wfm_user', JSON.stringify(user));
}

export function clearCurrentUser(): void {
  localStorage.removeItem('wfm_user');
}

export function getCurrentUser(): CurrentUser | null {
  const stored = localStorage.getItem('wfm_user');
  if (!stored) return null;
  try {
    return JSON.parse(stored) as CurrentUser;
  } catch {
    localStorage.removeItem('wfm_user');
    return null;
  }
}
```

Also update `clearCredentials` to also clear the user:

```typescript
export function clearCredentials(): void {
  localStorage.removeItem('wfm_credentials');
  clearCurrentUser();
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useCurrentUser.ts`**

```typescript
import { getCurrentUser, type CurrentUser } from '../api/client';

interface CurrentUserState {
  id: number;
  username: string;
  role: 'admin' | 'user';
  isAdmin: boolean;
}

export function useCurrentUser(): CurrentUserState | null {
  const user: CurrentUser | null = getCurrentUser();
  if (!user) return null;
  return { ...user, isAdmin: user.role === 'admin' };
}
```

- [ ] **Step 3: Update `frontend/src/pages/LoginPage.tsx`**

After the successful `res.ok` check, call `/api/me` and store the result. Replace the `if (res.ok)` block:

```typescript
      if (res.ok) {
        try {
          const me = await fetch('/api/users/me', {
            headers: { Authorization: `Basic ${btoa(`${username}:${password}`)}` },
          });
          if (me.ok) {
            const userData = await me.json();
            setCurrentUser(userData);
          }
        } catch {
          // non-fatal: role-based UI will degrade gracefully
        }
        qc.invalidateQueries();
        navigate('/');
      } else {
```

Add `setCurrentUser` to the import at the top:

```typescript
import { setCredentials, clearCredentials, setCurrentUser } from '../api/client';
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/hooks/useCurrentUser.ts frontend/src/pages/LoginPage.tsx
git commit -m "feat: store user role after login, add useCurrentUser hook"
```

---

## Task 6: Layout — profile button + admin nav filtering

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/ProfilePopover.tsx`

**Interfaces:**
- Consumes: `useCurrentUser()` from `../hooks/useCurrentUser`; `clearCredentials` from `../api/client`

- [ ] **Step 1: Create `frontend/src/components/ProfilePopover.tsx`**

```tsx
import { useState, useRef, useEffect } from 'react';
import { User, KeyRound, LogOut } from 'lucide-react';
import { apiPut } from '../api/client';
import { useCurrentUser } from '../hooks/useCurrentUser';

interface Props {
  onLogout: () => void;
}

function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== confirm) { setError('Passwörter stimmen nicht überein'); return; }
    if (next.length < 6) { setError('Passwort muss mindestens 6 Zeichen haben'); return; }
    setLoading(true);
    setError('');
    try {
      await apiPut('/users/me/password', { current_password: current, new_password: next });
      setSuccess(true);
      setTimeout(onClose, 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ändern des Passworts');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center px-4">
      <div className="bg-app-card border border-app-border rounded-2xl p-6 w-full max-w-sm shadow-lg">
        <h2 className="text-base font-semibold text-ink mb-4">Passwort ändern</h2>
        {success ? (
          <p className="text-sm text-signal-high">Passwort erfolgreich geändert.</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-ink-muted mb-1">Aktuelles Passwort</label>
              <input type="password" value={current} onChange={e => setCurrent(e.target.value)}
                className="input-field w-full" autoComplete="current-password" />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-1">Neues Passwort</label>
              <input type="password" value={next} onChange={e => setNext(e.target.value)}
                className="input-field w-full" autoComplete="new-password" />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-1">Bestätigen</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                className="input-field w-full" autoComplete="new-password" />
            </div>
            {error && <p className="text-xs text-signal-low">{error}</p>}
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={onClose}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-app-border text-ink-muted hover:bg-white/5">
                Abbrechen
              </button>
              <button type="submit" disabled={loading || !current || !next || !confirm}
                className="flex-1 btn-primary text-sm disabled:opacity-50">
                {loading ? 'Speichern...' : 'Speichern'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ProfilePopover({ onLogout }: Props) {
  const currentUser = useCurrentUser();
  const [open, setOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <>
      <div ref={ref} className="px-2 py-3 relative" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
          style={{ color: 'rgba(248,250,252,0.55)' }}
        >
          <User size={14} className="flex-shrink-0" />
          <span className="truncate flex-1 text-left">{currentUser?.username ?? 'Profil'}</span>
        </button>

        {open && (
          <div
            className="absolute bottom-full left-2 right-2 mb-1 rounded-[10px] border border-app-border shadow-lg overflow-hidden"
            style={{ background: '#1e293b' }}
          >
            <div className="px-3 py-2 border-b border-white/5">
              <p className="text-[12px] font-medium text-slate-200 truncate">{currentUser?.username}</p>
              <p className="text-[10px] mt-0.5" style={{ color: 'rgba(248,250,252,0.35)' }}>
                {currentUser?.role === 'admin' ? 'Administrator' : 'User'}
              </p>
            </div>
            <button
              onClick={() => { setOpen(false); setShowPasswordModal(true); }}
              className="flex items-center gap-2 w-full px-3 py-2 text-[12px] text-left hover:bg-white/5 transition-colors"
              style={{ color: 'rgba(248,250,252,0.55)' }}
            >
              <KeyRound size={13} />
              Passwort ändern
            </button>
            <button
              onClick={onLogout}
              className="flex items-center gap-2 w-full px-3 py-2 text-[12px] text-left hover:bg-white/5 transition-colors"
              style={{ color: 'rgba(248,250,252,0.45)' }}
            >
              <LogOut size={13} />
              Abmelden
            </button>
          </div>
        )}
      </div>

      {showPasswordModal && <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />}
    </>
  );
}
```

- [ ] **Step 2: Update `frontend/src/components/Layout.tsx`**

Replace `LogoutButton` component and its usage with `ProfilePopover`. Also filter admin nav based on role.

At the top, add imports:
```typescript
import ProfilePopover from './ProfilePopover';
import { useCurrentUser } from '../hooks/useCurrentUser';
```

Remove the `LogOut` import from lucide (keep the rest).

Replace the `LogoutButton` component definition with nothing (delete it).

In `NavItems`, filter the Admin section to only show admin items when the user is an admin. Modify `NavItems` to accept and use role:

```tsx
const ADMIN_ONLY_PATHS = ['/admin/sources', '/admin/schedule', '/admin/logs', '/admin/llm-usage', '/admin/settings', '/admin/users'];

function NavItems({ onNavClick, isAdmin }: { onNavClick?: () => void; isAdmin: boolean }) {
  return (
    <div className="flex-1 overflow-y-auto">
      {navSections.map((section) => {
        const items = section.label === 'Admin'
          ? section.items.filter(item => isAdmin || !ADMIN_ONLY_PATHS.includes(item.to))
          : section.items;
        if (items.length === 0) return null;
        return (
          <div key={section.label} className="pt-3.5 pb-1 px-2">
            <p className="text-[9px] font-semibold uppercase px-2 mb-1 tracking-widest"
              style={{ color: 'rgba(248,250,252,0.20)' }}>
              {section.label}
            </p>
            {items.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                onClick={onNavClick}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-2 py-[7px] rounded-[7px] text-[13px] font-medium mb-px transition-colors ${
                    isActive ? 'text-[#93c5fd]' : 'hover:bg-white/5 hover:text-slate-200'
                  }`
                }
                style={({ isActive }) => ({
                  background: isActive ? 'rgba(37,99,235,0.18)' : undefined,
                  color: isActive ? '#93c5fd' : 'rgba(248,250,252,0.45)',
                })}
              >
                <Icon size={15} className="flex-shrink-0" />
                {label}
              </NavLink>
            ))}
          </div>
        );
      })}
    </div>
  );
}
```

In the `Layout` function, add:
```tsx
const currentUser = useCurrentUser();
const isAdmin = currentUser?.isAdmin ?? false;
```

Replace all `<LogoutButton onLogout={handleLogout} />` with `<ProfilePopover onLogout={handleLogout} />`.

Replace all `<NavItems />` / `<NavItems onNavClick={...} />` with `<NavItems isAdmin={isAdmin} />` / `<NavItems isAdmin={isAdmin} onNavClick={...} />`.

Also add Users admin link to the `navSections` Admin section items array:
```typescript
{ to: '/admin/users', label: 'Benutzer', icon: Users },
```

(Note: `Users` icon is already imported from lucide-react)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProfilePopover.tsx frontend/src/components/Layout.tsx
git commit -m "feat: replace logout button with profile popover, filter admin nav by role"
```

---

## Task 7: Admin route guard + hide write-action UI elements

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/WeeklyDigestPage.tsx`
- Modify: `frontend/src/pages/SearchPage.tsx`

**Interfaces:**
- Consumes: `useCurrentUser` hook

- [ ] **Step 1: Add admin route guard and UsersAdminPage route to `App.tsx`**

Add import for a new `AdminGate` inline guard and the users page (which we'll create in Task 8). For now, add the route with a placeholder that redirects if not admin.

Add import at top:
```typescript
import { Navigate } from 'react-router-dom';
import { getCurrentUser } from './api/client';
```

Add a simple guard component inside `App.tsx` (above the `App` function):
```tsx
function AdminOnly({ children }: { children: React.ReactNode }) {
  const user = getCurrentUser();
  if (!user || user.role !== 'admin') return <Navigate to="/" replace />;
  return <>{children}</>;
}
```

Add the route inside the `<Route element={<AuthGate>...}>` block:
```tsx
<Route path="admin/users" element={<AdminOnly><UsersAdminPage /></AdminOnly>} />
```

Add the import (once UsersAdminPage is created in Task 8 — for now add a stub import note). Skip for this step; complete in Task 8.

- [ ] **Step 2: Hide "Generate New Digest" for non-admin in `WeeklyDigestPage.tsx`**

Add import at top:
```typescript
import { useCurrentUser } from '../hooks/useCurrentUser';
```

Inside the `WeeklyDigestPage` function, add:
```typescript
const currentUser = useCurrentUser();
```

Wrap the generate button (lines ~323-330) with a conditional:
```tsx
{currentUser?.isAdmin && (
  <button
    onClick={() => generateDigest.mutate()}
    disabled={generateDigest.isPending}
    className="btn-primary flex items-center gap-2 flex-shrink-0"
  >
    <RefreshCw size={16} className={generateDigest.isPending ? 'animate-spin' : ''} />
    {generateDigest.isPending ? 'Generating...' : 'Generate New Digest'}
  </button>
)}
```

Also wrap the error message block with `{currentUser?.isAdmin && (...)}`.

- [ ] **Step 3: Hide Approve/Reject in `SearchPage.tsx`**

Add import at top:
```typescript
import { useCurrentUser } from '../hooks/useCurrentUser';
```

Inside the component, add:
```typescript
const currentUser = useCurrentUser();
```

Wrap the approve/reject button block (lines ~328-345) with a conditional:
```tsx
{c.status === 'candidate' && currentUser?.isAdmin && (
  <div className="flex gap-2 shrink-0">
    <button onClick={() => setApproving(c)} ...>
      <CheckCircle size={13} />
      Approve
    </button>
    <button onClick={() => reject.mutate(c.id)} ...>
      <XCircle size={13} />
      Reject
    </button>
  </div>
)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/WeeklyDigestPage.tsx frontend/src/pages/SearchPage.tsx
git commit -m "feat: add admin route guard, hide write actions for non-admin users"
```

---

## Task 8: UsersAdminPage

**Files:**
- Create: `frontend/src/pages/UsersAdminPage.tsx`
- Modify: `frontend/src/App.tsx` — add import + route

**Interfaces:**
- Consumes: `apiGet`, `apiPost`, `apiPut`, `apiDelete` from `../api/client`

- [ ] **Step 1: Create `frontend/src/pages/UsersAdminPage.tsx`**

```tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Pencil } from 'lucide-react';
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
}

interface CreateUserPayload {
  username: string;
  password: string;
  role: 'admin' | 'user';
}

function useUsers() {
  return useQuery<User[]>({ queryKey: ['users'], queryFn: () => apiGet('/users') });
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'user'>('user');
  const [error, setError] = useState('');

  const create = useMutation({
    mutationFn: (payload: CreateUserPayload) => apiPost<User>('/users', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); onClose(); },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center px-4">
      <div className="bg-app-card border border-app-border rounded-2xl p-6 w-full max-w-sm shadow-lg">
        <h2 className="text-base font-semibold text-ink mb-4">Neuer Benutzer</h2>
        <form onSubmit={e => { e.preventDefault(); create.mutate({ username, password, role }); }} className="space-y-3">
          <div>
            <label className="block text-xs text-ink-muted mb-1">Benutzername</label>
            <input value={username} onChange={e => setUsername(e.target.value)} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-1">Passwort</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-1">Rolle</label>
            <select value={role} onChange={e => setRole(e.target.value as 'admin' | 'user')} className="input-field w-full">
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {error && <p className="text-xs text-signal-low">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-app-border text-ink-muted hover:bg-white/5">
              Abbrechen
            </button>
            <button type="submit" disabled={!username || !password || create.isPending}
              className="flex-1 btn-primary text-sm disabled:opacity-50">
              {create.isPending ? 'Erstellen...' : 'Erstellen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function UsersAdminPage() {
  const { data: users = [], isLoading } = useUsers();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState('');

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => apiPut<User>(`/users/${id}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiPut<User>(`/users/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  const deleteUser = useMutation({
    mutationFn: (id: number) => apiDelete(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-ink">Benutzerverwaltung</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Neuer Benutzer
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">{error}</div>
      )}

      {isLoading ? (
        <p className="text-ink-muted text-sm">Lade...</p>
      ) : (
        <div className="bg-app-card border border-app-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-app-border">
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Benutzer</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Rolle</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Erstellt</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-b border-app-border last:border-0 hover:bg-white/2">
                  <td className="px-4 py-3 font-medium text-ink">{user.username}</td>
                  <td className="px-4 py-3">
                    <select
                      value={user.role}
                      onChange={e => updateRole.mutate({ id: user.id, role: e.target.value })}
                      className="text-xs bg-transparent border border-app-border rounded px-2 py-1 text-ink"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                      className={`text-xs px-2 py-1 rounded font-medium ${
                        user.is_active
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}
                    >
                      {user.is_active ? 'Aktiv' : 'Inaktiv'}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-ink-muted text-xs">
                    {new Date(user.created_at).toLocaleDateString('de-DE')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => { if (confirm(`${user.username} löschen?`)) deleteUser.mutate(user.id); }}
                      className="text-ink-muted hover:text-signal-low transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
```

- [ ] **Step 2: Register route in `frontend/src/App.tsx`**

Add import:
```typescript
import UsersAdminPage from './pages/UsersAdminPage';
```

The route was already added in Task 7 (`<Route path="admin/users" element={<AdminOnly><UsersAdminPage /></AdminOnly>} />`). If it was skipped, add it now inside the authenticated route block.

- [ ] **Step 3: Start dev server and verify**

```bash
docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml up -d
```

Manual checks:
1. Log in as admin → see all nav items, see "Generate New Digest", see Approve/Reject on search candidates
2. Navigate to `/admin/users` → see user list, create a new user
3. Log out, log in as the new user-role user → admin nav items hidden, Generate/Approve/Reject hidden
4. Navigate to `/admin/users` directly → redirected to `/`
5. In bottom nav, click profile → popover shows username + role, "Passwort ändern" opens modal

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/UsersAdminPage.tsx frontend/src/App.tsx
git commit -m "feat: add UsersAdminPage for user management"
```
