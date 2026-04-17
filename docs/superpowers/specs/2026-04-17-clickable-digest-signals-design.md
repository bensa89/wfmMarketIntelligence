# Clickable Digest Signals — Design

## Goal
Make weekly digest signals clickable so users can navigate directly to the source article/page.

## Current State
- `DigestRead.key_signals` is `List[str]` (signal IDs only)
- `SignalRead` has `document_id` but no `source_url`
- `Document` model stores the original `url`
- Frontend `WeeklyDigest` page fetches ALL signals via `useSignals()` and resolves IDs client-side via `.find()` — no links to source articles

## Design

### Backend

#### 1. New schema: `DigestSignalRead` (in `backend/app/schemas/digest.py`)
```python
class DigestSignalRead(BaseModel):
    id: str
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    relevance_score: Optional[float]
    confidence_score: Optional[float]
    source_url: Optional[str]    # from document.url
    company_name: Optional[str]   # from company.name
```

#### 2. Expand `DigestRead.key_signals`
- Change from `List[str]` to `List[DigestSignalRead]`
- Digest router queries signals with `selectinload` on `document` and `company` relationships
- `source_url` is populated from `signal.document.url`
- `company_name` from `signal.company.name`

#### 3. Add `source_url` to `SignalRead` (in `backend/app/schemas/signal.py`)
- New field: `source_url: Optional[str]`
- Populated via joinedload on `signal.document` in signal router queries

#### 4. Digest generation (`POST /digests/generate`)
- `key_signals` column stays as `List[str]` (IDs) in the DB — expansion happens on read, not write
- This keeps the DB schema simple and signals always reflect latest data

### Frontend

#### 1. Update types (`frontend/src/types/index.ts`)
```typescript
interface DigestSignal {
  id: string;
  title: string;
  signal_type: string;
  topic: string | null;
  summary: string | null;
  relevance_score: number | null;
  confidence_score: number | null;
  source_url: string | null;
  company_name: string | null;
}

interface Digest {
  // ...existing fields
  key_signals: DigestSignal[];  // was string[]
}
```

#### 2. Update `WeeklyDigest` page
- Remove `useSignals()` fetch — signals come embedded in digest response
- Render each signal from `digest.key_signals` directly
- Make signal title/source a clickable link: `<a href={signal.source_url} target="_blank" rel="noopener noreferrer">`
- Add external-link icon next to title when `source_url` exists

#### 3. Optionally update `SignalCard` component
- Accept optional `sourceUrl` prop
- Render external link icon when `sourceUrl` is present

### Tests
- Update existing digest tests (key_signals format changed)
- Add test: `GET /digests/:id` returns expanded signals with source_url
- Add test: `GET /signals` returns source_url from document relation