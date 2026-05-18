# Competitor Logos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins upload a logo per competitor company; display it everywhere companies appear, with an initials-avatar fallback using existing color mapping.

**Architecture:** Logos are stored on disk under `/uploads/logos/{slug}.{ext}` (Docker volume), served by FastAPI's `StaticFiles` at `/static/`, and displayed via a single `CompanyLogo` React component (3 sizes) used across all views.

**Tech Stack:** Python/FastAPI (`python-multipart`, `StaticFiles`), SQLAlchemy + Alembic, React 18 + TypeScript, TanStack React Query, Tailwind CSS.

> **Run all backend tests inside Docker:**
> ```bash
> docker compose -f /Users/benjaminsaure/dev/wfmMarketIntelligence/docker-compose.dev.yml exec backend python -m pytest tests/ -v
> ```

---

## File Map

| Action | Path |
|--------|------|
| Modify | `backend/app/models/company.py` |
| Modify | `backend/app/schemas/company.py` |
| Modify | `backend/app/routers/companies.py` |
| Modify | `backend/app/main.py` |
| Create | `backend/alembic/versions/XXXX_add_logo_path_to_companies.py` |
| Modify | `docker-compose.dev.yml` |
| Modify | `docker-compose.yml` |
| Modify | `backend/tests/test_companies.py` |
| Modify | `frontend/src/types/index.ts` |
| Modify | `frontend/src/api/client.ts` |
| Modify | `frontend/src/hooks/useCompanies.ts` |
| Create | `frontend/src/components/CompanyLogo.tsx` |
| Modify | `frontend/src/pages/CompetitorDetail.tsx` |
| Modify | `frontend/src/components/workspace/CompetitorHeader.tsx` |
| Modify | `frontend/src/pages/CompetitorList.tsx` |
| Modify | `frontend/src/components/dashboard/CompanySignalHeatmap.tsx` |
| Modify | `frontend/src/components/SignalCard.tsx` |
| Modify | `frontend/src/components/signals/SignalDetailDrawer.tsx` |
| Modify | `frontend/src/components/FilterBar.tsx` |

---

## Task 1: Add `logo_path` to Company model and schema

**Files:**
- Modify: `backend/app/models/company.py`
- Modify: `backend/app/schemas/company.py`
- Test: `backend/tests/test_companies.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_companies.py`:

```python
def test_company_read_includes_logo_path(client):
    client.post(
        "/api/companies",
        json={"name": "ATOSS", "slug": "atoss-logo", "type": "competitor"},
    )
    response = client.get("/api/companies/atoss-logo")
    assert response.status_code == 200
    data = response.json()
    assert "logo_path" in data
    assert data["logo_path"] is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_companies.py::test_company_read_includes_logo_path -v
```

Expected: FAIL — `KeyError: 'logo_path'` or assertion error.

- [ ] **Step 3: Add `logo_path` to the model**

In `backend/app/models/company.py`, add after the `website` column:

```python
logo_path = Column(String(500), nullable=True)
```

Full file after change:

```python
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base

class CompanyType(str, enum.Enum):
    competitor = "competitor"
    market_source = "market_source"

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    type = Column(SAEnum(CompanyType), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    logo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="company")
```

- [ ] **Step 4: Add `logo_path` to the schema**

In `backend/app/schemas/company.py`, update `CompanyRead`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.company import CompanyType

class CompanyCreate(BaseModel):
    name: str
    slug: str
    type: CompanyType
    description: Optional[str] = None
    website: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None

class CompanyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    slug: str
    type: CompanyType
    description: Optional[str]
    website: Optional[str]
    logo_path: Optional[str] = None
    created_at: datetime
```

- [ ] **Step 5: Run test to verify it passes**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_companies.py::test_company_read_includes_logo_path -v
```

Expected: PASS (schema change is enough; migration comes next).

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/models/company.py backend/app/schemas/company.py backend/tests/test_companies.py
rtk git commit -m "feat: add logo_path field to Company model and schema"
```

---

## Task 2: Alembic migration

**Files:**
- Create: `backend/alembic/versions/XXXX_add_logo_path_to_companies.py`

- [ ] **Step 1: Generate the migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_logo_path_to_companies"
```

This creates a file under `backend/alembic/versions/`. Open it and verify it looks like:

```python
def upgrade() -> None:
    op.add_column('companies', sa.Column('logo_path', sa.String(length=500), nullable=True))

def downgrade() -> None:
    op.drop_column('companies', 'logo_path')
```

If it doesn't auto-detect correctly, edit the file to match the above.

- [ ] **Step 2: Apply the migration**

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Expected output ends with: `Running upgrade ... -> ..., add_logo_path_to_companies`

- [ ] **Step 3: Verify existing tests still pass**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_companies.py -v
```

Expected: all existing tests PASS.

- [ ] **Step 4: Commit**

```bash
rtk git add backend/alembic/versions/
rtk git commit -m "feat: migrate companies table to add logo_path column"
```

---

## Task 3: Docker volumes + StaticFiles mount

**Files:**
- Modify: `backend/app/main.py`
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add StaticFiles mount to `main.py`**

Add these imports at the top of `backend/app/main.py` (after existing imports):

```python
import os
import pathlib
from fastapi.staticfiles import StaticFiles
```

After the `app = FastAPI(...)` block and before `app.add_middleware(...)`, add:

```python
UPLOAD_DIR = pathlib.Path("/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "logos").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")
```

The full relevant section of `main.py` after the change:

```python
import os
import pathlib
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import secrets
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
    correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
)

UPLOAD_DIR = pathlib.Path("/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "logos").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ... rest unchanged
```

- [ ] **Step 2: Add `python-multipart` to backend dependencies**

Check if `python-multipart` is already in `backend/requirements.txt` (or `pyproject.toml`). If not, add it:

```bash
# Check:
grep -i multipart backend/requirements.txt || grep -i multipart backend/pyproject.toml

# If missing, add to requirements.txt:
echo "python-multipart>=0.0.9" >> backend/requirements.txt

# Then rebuild the backend container:
docker compose -f docker-compose.dev.yml build backend
docker compose -f docker-compose.dev.yml up -d backend
```

- [ ] **Step 3: Add uploads volume to `docker-compose.dev.yml`**

In the `backend` service, add a volume mount. In the `volumes` top-level section, add the named volume:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    ports:
      - "5435:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - uploads_data:/uploads
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    depends_on:
      - backend

volumes:
  postgres_data_dev:
  frontend_node_modules:
  uploads_data:
```

- [ ] **Step 4: Add uploads volume to `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: wfm
      POSTGRES_PASSWORD: wfm
      POSTGRES_DB: wfmintel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5435:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wfm"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - uploads_data:/uploads
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  uploads_data:
```

- [ ] **Step 5: Restart and verify `/static` is reachable**

```bash
docker compose -f docker-compose.dev.yml up -d backend
```

Verify (replace `user:pass` with real credentials):

```bash
curl -u user:pass http://localhost:8000/static/
```

Expected: 200 or 404 (directory listing not enabled is fine — what matters is no 500 error).

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/main.py docker-compose.dev.yml docker-compose.yml backend/requirements.txt
rtk git commit -m "feat: mount /uploads as StaticFiles and add Docker volume for logo persistence"
```

---

## Task 4: Logo upload endpoint + tests

**Files:**
- Modify: `backend/app/routers/companies.py`
- Modify: `backend/tests/test_companies.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `backend/tests/test_companies.py`:

```python
import io
import pathlib
from unittest.mock import patch

FAKE_UPLOAD_DIR = pathlib.Path("/tmp/test_uploads")

def _make_png() -> bytes:
    # 1×1 red pixel PNG (valid PNG, tiny)
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )

def test_upload_logo_png(client):
    client.post("/api/companies", json={"name": "Test Co", "slug": "test-co", "type": "competitor"})
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/test-co/logo",
            files={"file": ("logo.png", io.BytesIO(_make_png()), "image/png")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["logo_path"] == "logos/test-co.png"

def test_upload_logo_svg(client):
    client.post("/api/companies", json={"name": "SVG Co", "slug": "svg-co", "type": "competitor"})
    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/svg-co/logo",
            files={"file": ("logo.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )
    assert response.status_code == 200
    assert response.json()["logo_path"] == "logos/svg-co.svg"

def test_upload_logo_invalid_mime(client):
    client.post("/api/companies", json={"name": "Bad Co", "slug": "bad-co", "type": "competitor"})
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/bad-co/logo",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
    assert response.status_code == 400
    assert "Ungültiger Dateityp" in response.json()["detail"]

def test_upload_logo_too_large(client):
    client.post("/api/companies", json={"name": "Big Co", "slug": "big-co", "type": "competitor"})
    large_file = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/big-co/logo",
            files={"file": ("big.png", large_file, "image/png")},
        )
    assert response.status_code == 400
    assert "zu groß" in response.json()["detail"]

def test_upload_logo_replaces_old_file(client):
    client.post("/api/companies", json={"name": "Re Co", "slug": "re-co", "type": "competitor"})
    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # Upload PNG first
        client.post(
            "/api/companies/re-co/logo",
            files={"file": ("logo.png", io.BytesIO(_make_png()), "image/png")},
        )
        # Upload SVG — old PNG should be deleted
        response = client.post(
            "/api/companies/re-co/logo",
            files={"file": ("logo.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )
    assert response.status_code == 200
    assert response.json()["logo_path"] == "logos/re-co.svg"
    # Old file should not exist
    assert not (FAKE_UPLOAD_DIR / "re-co.png").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_companies.py::test_upload_logo_png tests/test_companies.py::test_upload_logo_svg tests/test_companies.py::test_upload_logo_invalid_mime tests/test_companies.py::test_upload_logo_too_large tests/test_companies.py::test_upload_logo_replaces_old_file -v
```

Expected: all FAIL — `404 Not Found` (endpoint doesn't exist yet).

- [ ] **Step 3: Implement the upload endpoint**

Replace the entire content of `backend/app/routers/companies.py` with:

```python
import pathlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter()

LOGO_DIR = pathlib.Path("/uploads/logos")
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB

MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/svg+xml": "svg",
}


@router.get("", response_model=List[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    existing = db.query(Company).filter(Company.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{slug}", response_model=CompanyRead)
def get_company(slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{slug}", response_model=CompanyRead)
def update_company(slug: str, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


@router.post("/{slug}/logo", response_model=CompanyRead)
async def upload_logo(
    slug: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Dateityp: {file.content_type}. Erlaubt: PNG, JPG, SVG.",
        )

    contents = await file.read()
    if len(contents) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Datei zu groß. Maximum: 2 MB.")

    ext = MIME_TO_EXT[file.content_type]

    # Delete old logo file if extension changed
    if company.logo_path:
        old_file = LOGO_DIR.parent / company.logo_path
        if old_file.exists():
            old_file.unlink()

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    dest = LOGO_DIR / f"{slug}.{ext}"
    dest.write_bytes(contents)

    company.logo_path = f"logos/{slug}.{ext}"
    db.commit()
    db.refresh(company)
    return company
```

- [ ] **Step 4: Run the upload tests**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/test_companies.py::test_upload_logo_png tests/test_companies.py::test_upload_logo_svg tests/test_companies.py::test_upload_logo_invalid_mime tests/test_companies.py::test_upload_logo_too_large tests/test_companies.py::test_upload_logo_replaces_old_file -v
```

Expected: all PASS.

- [ ] **Step 5: Run the full test suite**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/routers/companies.py backend/tests/test_companies.py
rtk git commit -m "feat: add logo upload endpoint POST /api/companies/{slug}/logo"
```

---

## Task 5: Frontend — types + API upload function

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `logo_path` to the `Company` type**

In `frontend/src/types/index.ts`, update the `Company` interface:

```typescript
export interface Company {
  id: string;
  name: string;
  slug: string;
  type: CompanyType;
  description: string | null;
  website: string | null;
  logo_path: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Add `apiPostFormData` to the API client**

In `frontend/src/api/client.ts`, add this function after `apiDelete`:

```typescript
export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: authHeader(), // no Content-Type — fetch sets multipart boundary automatically
    body: formData,
  });
  if (res.status === 401) throw new ApiError(401, 'Authentication required');
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  return res.json();
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no errors (or only pre-existing errors unrelated to this change).

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/types/index.ts frontend/src/api/client.ts
rtk git commit -m "feat: add logo_path to Company type and apiPostFormData to API client"
```

---

## Task 6: `CompanyLogo` component

**Files:**
- Create: `frontend/src/components/CompanyLogo.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/CompanyLogo.tsx`:

```typescript
import { getCompanyColor } from './dashboard/CompanyColorMap';

interface CompanyLogoProps {
  name: string;
  slug: string;
  logo_path?: string | null;
  size: 'sm' | 'md' | 'lg';
  companyId?: string; // used for color lookup when no logo
}

const SIZE_PX: Record<'sm' | 'md' | 'lg', number> = {
  sm: 24,
  md: 36,
  lg: 56,
};

const FONT_SIZE: Record<'sm' | 'md' | 'lg', string> = {
  sm: '9px',
  md: '13px',
  lg: '20px',
};

export default function CompanyLogo({ name, slug, logo_path, size, companyId }: CompanyLogoProps) {
  const px = SIZE_PX[size];
  const initials = name.slice(0, 2).toUpperCase();
  const bgColor = getCompanyColor(companyId ?? slug);

  const containerStyle: React.CSSProperties = {
    width: px,
    height: px,
    minWidth: px,
    borderRadius: 6,
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  };

  if (logo_path) {
    return (
      <div
        style={{
          ...containerStyle,
          background: '#fff',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.08)',
          padding: size === 'lg' ? 4 : 2,
        }}
      >
        <img
          src={`/static/${logo_path}`}
          alt={name}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => {
            // If image fails to load, hide img and show initials via parent re-render isn't possible,
            // so we replace the src with an empty placeholder to stop retrying
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        ...containerStyle,
        background: bgColor,
        color: '#fff',
        fontSize: FONT_SIZE[size],
        fontWeight: 700,
        letterSpacing: '0.02em',
      }}
    >
      {initials}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
rtk git add frontend/src/components/CompanyLogo.tsx
rtk git commit -m "feat: add CompanyLogo component with logo/initials-avatar fallback"
```

---

## Task 7: Upload UI in CompetitorDetail + useUploadCompanyLogo hook

**Files:**
- Modify: `frontend/src/hooks/useCompanies.ts`
- Modify: `frontend/src/pages/CompetitorDetail.tsx`

- [ ] **Step 1: Add `useUploadCompanyLogo` hook**

In `frontend/src/hooks/useCompanies.ts`, add at the end of the file:

```typescript
import { apiPostFormData } from '../api/client';

export function useUploadCompanyLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, file }: { slug: string; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiPostFormData<Company>(`/companies/${slug}/logo`, formData);
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      qc.invalidateQueries({ queryKey: ['companies', variables.slug] });
    },
  });
}
```

Make sure `apiPostFormData` is imported at the top of the file alongside the other api imports:

```typescript
import { apiGet, apiPost, apiPut, apiDelete, apiPostFormData } from '../api/client';
```

- [ ] **Step 2: Add logo display + upload UI in CompetitorDetail**

Open `frontend/src/pages/CompetitorDetail.tsx`. 

Add these imports at the top:

```typescript
import CompanyLogo from '../components/CompanyLogo';
import { useUploadCompanyLogo } from '../hooks/useCompanies';
```

Add the hook inside the component (after existing hooks):

```typescript
const uploadLogo = useUploadCompanyLogo();
const [uploadError, setUploadError] = useState<string | null>(null);

function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file || !company) return;
  setUploadError(null);
  uploadLogo.mutate(
    { slug: company.slug, file },
    { onError: (err) => setUploadError(err instanceof Error ? err.message : 'Upload fehlgeschlagen') },
  );
  e.target.value = ''; // reset so same file can be re-selected
}
```

Find the section in the JSX that renders the company name (look for `<h1>` or similar with `company.name`). Add the logo + upload UI just before or alongside it:

```tsx
{/* Company header with logo */}
<div className="flex items-center gap-3 mb-4">
  <CompanyLogo
    name={company.name}
    slug={company.slug}
    logo_path={company.logo_path}
    size="lg"
    companyId={company.id}
  />
  <div>
    <h1 className="text-xl font-bold text-slate-900">{company.name}</h1>
    {company.website && (
      <a
        href={company.website}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[12px] text-blue-600 hover:text-blue-700"
      >
        {company.website}
      </a>
    )}
    <div className="mt-1 flex items-center gap-2">
      <label className="cursor-pointer text-[11px] px-2 py-1 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors font-medium">
        {uploadLogo.isPending ? 'Wird hochgeladen…' : 'Logo hochladen'}
        <input
          type="file"
          accept="image/png,image/jpeg,image/svg+xml"
          className="hidden"
          onChange={handleLogoChange}
          disabled={uploadLogo.isPending}
        />
      </label>
      {uploadError && (
        <span className="text-[11px] text-red-600">{uploadError}</span>
      )}
    </div>
  </div>
</div>
```

Remove any existing standalone `<h1>{company.name}</h1>` and website link that you replaced.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/hooks/useCompanies.ts frontend/src/pages/CompetitorDetail.tsx
rtk git commit -m "feat: add logo upload UI to CompetitorDetail and useUploadCompanyLogo hook"
```

---

## Task 8: Logo in CompetitorHeader + CompetitorList

**Files:**
- Modify: `frontend/src/components/workspace/CompetitorHeader.tsx`
- Modify: `frontend/src/pages/CompetitorList.tsx`

- [ ] **Step 1: Update CompetitorHeader**

The `CompetitorHeader` receives `profile: WorkspaceResponse['competitor_profile']`. Check what fields `competitor_profile` has in `frontend/src/types/intelligence.ts`. It has at minimum `id`, `name`, `description`, `website`.

If `competitor_profile` does not have `logo_path` and `slug`, you have two options:
- **A (preferred):** Add `logo_path: string | null` and `slug: string` to the `competitor_profile` type in `intelligence.ts`, and ensure the backend intelligence endpoint returns them.
- **B (fallback):** Use `useCompany(slug)` inside `CompetitorHeader` if slug is available in the URL.

For option A, update `frontend/src/types/intelligence.ts` — find the type for `competitor_profile` and add:

```typescript
logo_path: string | null;
slug: string;
```

Then update `CompetitorHeader.tsx` to show the logo:

```typescript
import { ExternalLink, RefreshCw } from 'lucide-react';
import { useSummarizeCompetitor } from '../../hooks/useSummarizeCompetitor';
import type { WorkspaceResponse } from '../../types/intelligence';
import CompanyLogo from '../CompanyLogo';

interface Props {
  profile: WorkspaceResponse['competitor_profile'];
}

export default function CompetitorHeader({ profile }: Props) {
  const summarize = useSummarizeCompetitor(profile.id);

  return (
    <div className="flex items-start justify-between mb-6">
      <div className="flex items-center gap-3">
        <CompanyLogo
          name={profile.name}
          slug={profile.slug ?? profile.id}
          logo_path={profile.logo_path ?? null}
          size="lg"
          companyId={profile.id}
        />
        <div>
          <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">{profile.name}</h1>
          {profile.description && (
            <p className="text-[13px] text-slate-600 mt-0.5 max-w-2xl">{profile.description}</p>
          )}
          {profile.website && (
            <a
              href={profile.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[12px] text-blue-600 hover:text-blue-700 mt-1 transition-colors"
            >
              <ExternalLink size={11} />
              {profile.website}
            </a>
          )}
        </div>
      </div>
      <button
        onClick={() => summarize.mutate('30d')}
        disabled={summarize.isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-white border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
        title="Regenerate 30d summary"
      >
        <RefreshCw size={13} className={summarize.isPending ? 'animate-spin' : ''} />
        Refresh Summary
      </button>
    </div>
  );
}
```

> **Note:** If `competitor_profile` doesn't have `slug`/`logo_path` from the backend, use `??` fallbacks as shown above — the initials avatar will appear until the backend is updated.

- [ ] **Step 2: Update CompetitorList**

Open `frontend/src/pages/CompetitorList.tsx`. Add the import at the top:

```typescript
import CompanyLogo from '../components/CompanyLogo';
```

Find where competitor rows are rendered (look for `.map` over `competitors` array rendering links). Each row currently shows just the company name. Add the logo before the name:

```tsx
{competitors.map((company) => (
  <div key={company.id} className="flex items-center gap-3 ...">
    <CompanyLogo
      name={company.name}
      slug={company.slug}
      logo_path={company.logo_path}
      size="md"
      companyId={company.id}
    />
    <div>
      {/* existing name + signal count content */}
    </div>
  </div>
))}
```

Do the same for `marketSources` rows.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/components/workspace/CompetitorHeader.tsx frontend/src/pages/CompetitorList.tsx frontend/src/types/intelligence.ts
rtk git commit -m "feat: show company logo in CompetitorHeader and CompetitorList"
```

---

## Task 9: Logo in CompanySignalHeatmap + SignalCard

**Files:**
- Modify: `frontend/src/components/dashboard/CompanySignalHeatmap.tsx`
- Modify: `frontend/src/components/SignalCard.tsx`

- [ ] **Step 1: Update CompanySignalHeatmap**

The heatmap currently receives `companies: { id: string; name: string }[]`. Update the prop type to use the full `Company` type so `slug` and `logo_path` are available.

Add the import at the top of `CompanySignalHeatmap.tsx`:

```typescript
import type { Company } from '../../types';
import CompanyLogo from '../CompanyLogo';
```

Update the interface:

```typescript
interface CompanySignalHeatmapProps {
  data: CompanySignalTypeCount[];
  companies: Company[];
}
```

In the JSX where competitor names are rendered (in the row headers), wrap with a flex container and add the logo:

```tsx
{/* Row header — before: just company name text */}
<div className="flex items-center gap-1.5 truncate">
  <CompanyLogo
    name={company.name}
    slug={company.slug}
    logo_path={company.logo_path}
    size="sm"
    companyId={company.id}
  />
  <span className="text-[11px] text-slate-700 font-medium truncate">{company.name}</span>
</div>
```

Check if the caller (likely `Dashboard.tsx`) passes `companies` — it should already pass the full `Company[]` from `useCompanies()`. If it was previously mapped to `{ id, name }`, remove that mapping so the full object is passed.

- [ ] **Step 2: Update SignalCard**

`SignalCard` currently has `companyName` and `companySlug` props but no logo. The caller must also pass `companyLogoPath`.

Add the import at the top of `SignalCard.tsx`:

```typescript
import CompanyLogo from './CompanyLogo';
```

Update the props interface:

```typescript
interface SignalCardProps {
  signal: Signal;
  showCompany?: boolean;
  companyName?: string;
  companySlug?: string;
  companyLogoPath?: string | null;
  companyId?: string;
  onClick?: () => void;
}
```

Update the destructuring:

```typescript
export default function SignalCard({ signal, showCompany = false, companyName, companySlug, companyLogoPath, companyId, onClick }: SignalCardProps) {
```

In the JSX, find where `showCompany && companyName` is rendered (look for a `<span>` or `<Link>` with company name). Replace it with:

```tsx
{showCompany && companyName && companySlug && (
  <div className="flex items-center gap-1.5 mt-1">
    <CompanyLogo
      name={companyName}
      slug={companySlug}
      logo_path={companyLogoPath}
      size="sm"
      companyId={companyId}
    />
    <Link
      to={`/competitors/${companySlug}`}
      className="text-[11px] text-slate-500 hover:text-slate-700 truncate"
      onClick={(e) => e.stopPropagation()}
    >
      {companyName}
    </Link>
  </div>
)}
```

Update all callers of `SignalCard` to pass `companyLogoPath` and `companyId`. Search for `<SignalCard` in the codebase:

```bash
grep -r "<SignalCard" /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend/src --include="*.tsx" -l
```

For each caller that passes `companyName`, also pass:

```tsx
companyLogoPath={company?.logo_path}
companyId={company?.id}
```

(where `company` is the `Company` object from `useCompanies()` or similar, looked up by the signal's `company_id`).

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

Fix any type errors from the prop changes.

- [ ] **Step 4: Commit**

```bash
rtk git add frontend/src/components/dashboard/CompanySignalHeatmap.tsx frontend/src/components/SignalCard.tsx
rtk git commit -m "feat: show company logo in CompanySignalHeatmap and SignalCard"
```

---

## Task 10: Logo in SignalDetailDrawer + FilterBar

**Files:**
- Modify: `frontend/src/components/signals/SignalDetailDrawer.tsx`
- Modify: `frontend/src/components/FilterBar.tsx`

- [ ] **Step 1: Update SignalDetailDrawer**

The drawer receives `item: SignalFeedItem` which has `company_id`. Use `useCompanies()` inside the drawer to look up the company and get its logo.

Add imports at the top of `SignalDetailDrawer.tsx`:

```typescript
import CompanyLogo from '../CompanyLogo';
import { useCompanies } from '../../hooks/useCompanies';
```

Inside the `SignalDetailDrawer` component, add:

```typescript
const { data: companies } = useCompanies();
const company = companies?.find((c) => c.id === item.company_id);
```

In the modal header JSX (the `<div>` containing `signal-modal-title`), add the logo before the title:

```tsx
<div className="flex items-start justify-between p-5 border-b border-slate-200 flex-shrink-0">
  <div className="flex items-start gap-3 flex-1 pr-4">
    {company && (
      <CompanyLogo
        name={company.name}
        slug={company.slug}
        logo_path={company.logo_path}
        size="sm"
        companyId={company.id}
      />
    )}
    <div className="flex-1 min-w-0">
      <div id="signal-modal-title" className="text-[16px] font-semibold text-slate-900 leading-snug">{item.title}</div>
      {item.source_url && (
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 mt-1 text-[11px] text-blue-600 hover:text-blue-700 transition-colors"
        >
          <ExternalLink size={11} className="flex-shrink-0" />
          {item.document_title || item.source_url}
        </a>
      )}
    </div>
  </div>
  <button onClick={onClose} aria-label="Schließen" className="text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0">
    <X size={16} />
  </button>
</div>
```

- [ ] **Step 2: Update FilterBar company dropdown**

Open `frontend/src/components/FilterBar.tsx`. The `companies` prop is `{ id: string; name: string; type: CompanyType }[]`. Update the type to use the full `Company`:

```typescript
import type { SignalType, Company } from '../types';
```

Update the prop:

```typescript
companies?: Company[];
```

Find where company options are rendered in the dropdown (look for `.map` over `companies`). Add the logo:

```typescript
import CompanyLogo from './CompanyLogo';
```

In the dropdown option rendering:

```tsx
{companies?.map((c) => (
  <option key={c.id} value={c.id}>{c.name}</option>
))}
```

Since `<select>/<option>` doesn't support custom HTML, replace the native select with a custom button-list if you want logos. However, to keep scope minimal, use a `<select>` with a plain name — logos in selects aren't supported in HTML. Instead, if there's a custom dropdown already (check if it's a `<select>` or a custom component):

- If native `<select>`: keep as-is (logos don't work in native selects), no change needed.
- If custom dropdown (list of `<button>` or `<div>` elements): add `<CompanyLogo>` before each company name.

Check the FilterBar implementation and apply logos only if there's a custom dropdown, otherwise skip this step for the FilterBar.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npx tsc --noEmit
```

- [ ] **Step 4: Run the full frontend build to confirm no errors**

```bash
cd /Users/benjaminsaure/dev/wfmMarketIntelligence/frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 5: Final backend test run**

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add frontend/src/components/signals/SignalDetailDrawer.tsx frontend/src/components/FilterBar.tsx
rtk git commit -m "feat: show company logo in SignalDetailDrawer and FilterBar"
```

---

## Done

All tasks complete. Logos can be uploaded via the CompetitorDetail admin area and appear across all competitor views. The initials avatar (from `CompanyColorMap`) shows as fallback when no logo is set.
