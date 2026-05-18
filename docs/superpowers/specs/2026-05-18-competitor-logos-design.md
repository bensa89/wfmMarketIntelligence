# Competitor Logos — Design Spec

**Date:** 2026-05-18  
**Status:** Approved

## Overview

Add logo upload and display for Competitor companies throughout the application. Logos improve at-a-glance identification of competitors across all views. When no logo is uploaded, an initials-based avatar (using the existing `CompanyColorMap` colors) is shown as fallback.

---

## Backend

### Database

Add nullable `logo_path` (String) field to the `Company` model via Alembic migration.

```python
logo_path: str | None = Column(String, nullable=True)
```

Expose `logo_path` in `CompanyRead` schema.

### File Storage

Logos are stored on disk at `/uploads/logos/{slug}.{ext}` inside the container. The `/uploads` directory is mounted as a Docker volume in both `docker-compose.dev.yml` and `docker-compose.yml` for persistence.

FastAPI mounts `/uploads` as static files:

```python
app.mount("/static", StaticFiles(directory="/uploads"), name="static")
```

Frontend accesses logos via `/static/logos/{slug}.{ext}`.

### Upload Endpoint

```
POST /api/companies/{slug}/logo
Content-Type: multipart/form-data
Auth: HTTP Basic (existing)
```

- Validates MIME type: `image/svg+xml`, `image/png`, `image/jpeg` only → 400 otherwise
- Validates file size: max 2 MB → 400 otherwise
- If `company.logo_path` is already set, deletes the old file from disk before writing the new one (avoids orphaned files when extension changes, e.g. `.png` → `.svg`)
- Writes file to `/uploads/logos/{slug}.{ext}`
- Sets `company.logo_path` to `logos/{slug}.{ext}` in DB (relative path, no leading slash)
- Returns updated `CompanyRead`

### Tests

- Upload happy path (PNG, SVG, JPG)
- Reject invalid MIME type → 400
- Reject file > 2 MB → 400
- `CompanyRead` includes `logo_path` when set

---

## Frontend

### `CompanyLogo` Component

Single reusable component placed in `frontend/src/components/CompanyLogo.tsx`.

**Props:**
```ts
interface CompanyLogoProps {
  company: { slug: string; name: string; logo_path?: string | null };
  size: 'sm' | 'md' | 'lg';
}
```

**Sizes:**

| Size | px  | Used in |
|------|-----|---------|
| `sm` | 24×24 | Heatmap, SignalCard, SignalDetailDrawer modal header, filter dropdowns |
| `md` | 36×36 | CompetitorList rows |
| `lg` | 56×56 | CompetitorHeader (workspace), CompetitorDetail |

**Display logic:**
- If `logo_path` is set → render `<img src={/static/${logo_path}} alt={company.name} />` with `object-fit: contain`
- Otherwise → render initials avatar (first 2 chars of name, uppercased) with background color from `CompanyColorMap`

**Container styling:**
- White background, `border-radius: 6px`, subtle `box-shadow`
- Padding inside container so logo never touches edges
- Fixed width/height per size

### Upload UI

Added to the existing company admin/detail area. Under the company name:

- Shows current logo (or initials avatar placeholder)
- Button "Logo hochladen" opens native file picker (SVG, PNG, JPG, max 2 MB)
- On select: `POST /api/companies/{slug}/logo`, invalidates React Query `companies` cache on success
- On error: toast error message, no state change
- Replaces existing logo on re-upload

### Integration Points

All existing components are updated to use `CompanyLogo` instead of plain text or color dots:

| Component | Size |
|-----------|------|
| `CompanySignalHeatmap` | `sm` before competitor name |
| `SignalCard` | `sm` as avatar |
| `SignalDetailDrawer` (modal header) | `sm` next to competitor name |
| `CompetitorList` rows | `md` |
| Filter dropdowns listing competitors | `sm` |
| `CompetitorHeader` (workspace) | `lg` |
| `CompetitorDetail` page | `lg` |

### Data Flow

1. Admin uploads file → `POST /api/companies/{slug}/logo`
2. Backend validates, writes file, updates `logo_path` in DB
3. Returns updated `CompanyRead`
4. React Query `companies` cache is invalidated
5. All views re-render automatically with new logo

### Error Handling

- Invalid MIME type or file too large → backend returns 400 → frontend shows toast error
- Network failure → toast error, no DB/file change
- Missing logo (null `logo_path`) → initials avatar fallback, no broken image shown

### Tests

- `CompanyLogo` renders `<img>` when `logo_path` is set
- `CompanyLogo` renders initials avatar when `logo_path` is null
- Upload UI calls correct endpoint and invalidates cache on success
