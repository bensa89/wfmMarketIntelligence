# Signal Publication Date — Design Spec
_2026-04-21_

## Problem

Signals entstehen aus gescrapten Artikeln, haben aber kein verlässliches Publikationsdatum. Aktuell:
- `Document.published_at` existiert im DB-Schema, wird aber nie gesetzt
- Der HTML-Extraktor extrahiert kein Datum aus Metadaten
- Das LLM schätzt `published_at` aus dem Content — unzuverlässig
- Im Frontend: stiller Fallback auf `created_at` wenn `published_at` null → irreführend
- Artikel von 2024 erzeugen "neue" Signals ohne Altersfilter

## Ziel

1. Publikationsdatum verlässlich aus HTML-Metadaten extrahieren, LLM als Fallback
2. Artikel älter als 1 Jahr werden nicht analysiert (kein Signal, is_analysed=True)
3. Frontend zeigt `published_at` prominent; "Datum unbekannt" wenn null

---

## Backend

### 1. `backend/app/crawler/extractor.py`

**`ExtractionResult`** bekommt neues Feld:
```python
published_at: Optional[datetime] = None
```

**Neue Funktion `_extract_published_at(soup: BeautifulSoup) -> Optional[datetime]`**

Prüft in Prioritätsreihenfolge:
1. JSON-LD `<script type="application/ld+json">` → Feld `datePublished`
2. `<meta property="article:published_time" content="...">`
3. `<meta name="pubdate" content="...">` / `<meta name="date" content="...">`
4. Erstes `<time datetime="...">` Element mit nicht-leerem `datetime`-Attribut

Gibt das erste erfolgreich parsbare `datetime` zurück, sonst `None`.

Datum-Parsing: versucht nacheinander ISO-8601-Formate (`%Y-%m-%dT%H:%M:%S%z`, `%Y-%m-%dT%H:%M:%SZ`, `%Y-%m-%d`). Bei Fehler: `None`.

`extract_content()` ruft `_extract_published_at(soup)` auf und gibt das Ergebnis in `ExtractionResult` zurück.

---

### 2. `backend/app/crawler/pipeline.py`

Beim **Erstellen** eines neuen `Document`:
```python
doc = Document(
    ...
    published_at=extraction.published_at,  # neu
)
```

Beim **Update** eines bestehenden `Document` (Content geändert):
```python
if extraction.published_at and not existing_by_url.published_at:
    existing_by_url.published_at = extraction.published_at
```

Gleiches gilt für Dokumente, die über die Discovery-Pipeline erstellt werden (`backend/app/crawler/discovery.py`).

---

### 3. `backend/app/analyser/pipeline.py`

**Alterschwellwert:** `datetime.now(timezone.utc) - timedelta(days=365)`

> Hinweis: `doc.published_at` aus PostgreSQL ist naive datetime (kein tzinfo). Vergleich via `doc.published_at.replace(tzinfo=timezone.utc) < age_threshold`.

**Checkpoint 1 — vor LLM** (spart LLM-Kosten):
```python
if doc.published_at and doc.published_at < age_threshold:
    logger.info("Skipping doc %s: published_at %s is older than 1 year", doc.id, doc.published_at)
    doc.is_analysed = True
    db.commit()
    return
```

**Checkpoint 2 — nach LLM** (LLM-Fallback für Datum):
```python
if signal_data.published_at and signal_data.published_at < age_threshold:
    logger.info("Skipping signal for doc %s: LLM-detected published_at %s is older than 1 year", doc.id, signal_data.published_at)
    doc.is_analysed = True
    db.commit()
    return
```

Wenn kein Datum bekannt (weder HTML noch LLM) → Signal wird normal erstellt, `published_at = None`.

---

## Frontend

### Neue Hilfsfunktion `frontend/src/utils/dates.ts`

```typescript
export function formatPublishedAt(publishedAt: string | null): {
  label: string;
  isUnknown: boolean;
} {
  if (!publishedAt) return { label: 'Datum unbekannt', isUnknown: true };
  return {
    label: new Date(publishedAt).toLocaleDateString('de-DE'),
    isUnknown: false,
  };
}
```

Kein stiller Fallback auf `created_at` für die primäre Datumsanzeige.

---

### Komponenten-Änderungen

**`SignalCard.tsx`**
- Datum-Zeile: `formatPublishedAt(signal.published_at)`
- Wenn `isUnknown`: Grau + Kursiv (`text-ink-muted italic`)

**`SignalFeedTable.tsx`**
- "Datum"-Spalte: `formatPublishedAt(signal.published_at)`
- Wenn `isUnknown`: `—` in Grau

**`TopSignalsPanel.tsx`**
- Falls Datum angezeigt wird: gleiche Logik

**`SignalDocumentModal` (in `Dashboard.tsx`)**
- Primär: `published_at` mit "Datum unbekannt" wenn null
- Sekundär darunter: `Erfasst: <created_at>` als kleiner Grau-Text

---

## Nicht im Scope

- Backfill bestehender Dokumente (kein `published_at` für alte Datensätze)
- Konfigurierbarer Alterschwellwert (hardcoded 365 Tage)
- Änderung am LLM-Prompt (fragt bereits nach `published_at`)

---

## Betroffene Dateien

### Backend
- `backend/app/crawler/extractor.py` — `_extract_published_at`, `ExtractionResult`
- `backend/app/crawler/pipeline.py` — `published_at` beim Document speichern
- `backend/app/crawler/discovery.py` — gleiche Änderung für Discovery-Pfad
- `backend/app/analyser/pipeline.py` — zwei Alters-Checkpoints

### Frontend
- `frontend/src/utils/dates.ts` — neu: `formatPublishedAt`
- `frontend/src/components/SignalCard.tsx`
- `frontend/src/components/dashboard/SignalFeedTable.tsx`
- `frontend/src/components/dashboard/TopSignalsPanel.tsx`
- `frontend/src/pages/Dashboard.tsx` — `SignalDocumentModal`
