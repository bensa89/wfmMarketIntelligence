# Weekly Digest Redesign — Spec

**Date:** 2026-05-07  
**Status:** Approved

## Overview

Replace the current naive top-10-signals-by-score digest with a structured, LLM-curated weekly briefing organised into five fixed sections. Each section answers a specific competitive intelligence question. Output is rendered in the web UI and copyable as plain-text email.

---

## Goals

- Answer five standing questions every week: market movements, new trends, competitor activities, competitor news, events
- Show only 5–10 most important items across all sections — no filler
- No duplicates from the previous digest unless the signal has materially progressed
- Leverage existing `SignalAssessment` data (no re-analysis) — LLM only curates and narrates
- Support manual email dispatch: one-click copy to clipboard as plain text

---

## Sections

Five fixed sections rendered in this order. A section is omitted entirely when no qualifying signals exist.

| Key | Title | Primary Signal Types | Assessment Classes |
|---|---|---|---|
| `market_movements` | Marktbewegungen | `positioning_change`, `target_market_change` | `positioning_move`, `market_expansion_move` |
| `new_trends` | Neue Trends | `ai_announcement`, `other` | `product_capability_move`, `weak_signal` |
| `competitor_activities` | Wettbewerber-Aktivitäten | `product_update`, `partnership`, `hiring_signal` | `product_capability_move`, `ecosystem_move`, `hiring_signal` |
| `competitor_news` | Wettbewerber-News | any type, filtered by `source.type IN (news, press)` | — |
| `events` | Events & Thought Leadership | `event_or_thought_leadership` | `thought_leadership_signal` |

---

## Generation Logic

`POST /api/digests/generate` triggers the following pipeline. Each step is isolated per section.

### Per-Section Pipeline

1. **Candidate query**  
   Signals created within the digest's calendar week (Mon `week_start` – Sun `week_end`) matching the section's signal_type/assessment_class filter, ordered by `movement_score DESC`. Signals without an assessment are included but ranked last (no `movement_score`), using `relevance_score` as fallback. Max 15 candidates per section.

2. **Dedup filter**  
   Skip a signal if its `signal_id` appears in `last_digest.sections` **unless**:
   - Its `movement_strength` has improved (e.g. `relevant` → `strong`), **or**
   - It comes from a different `document_id` than the one in the previous digest (new event, same company)

3. **LLM curation call** (skipped if zero candidates after dedup)  
   Single call per section with:
   - Candidates: `title`, `company_name`, `assessment_summary`, `implication_for_us`, `strategic_intent_guess`, `movement_strength`, `source_url`, `source_domain`, `source_title`
   - Previous digest section content (same `key`) for context
   - `InternalCompanyContext` (capabilities, priorities, differentiators)
   - Instruction: select 1–3 most important items, write a 2–3 sentence connecting narrative per item. Do not add new analysis — only curate and reframe existing assessment data.

4. **Section output**  
   Structured JSON per item (see Data Model below).

### Intro Summary

After all sections are generated, one additional LLM call produces a 1–2 sentence intro (`summary` field) summarising the week's most important development across all sections.

---

## Data Model

### Migration

Add `sections` column to `weekly_digests` table:

```sql
ALTER TABLE weekly_digests ADD COLUMN sections JSON;
```

Alembic autogenerate migration. `key_signals` and `summary` columns are preserved for backwards compatibility. `key_signals` is no longer populated by new generation runs.

### `sections` JSON Schema

```json
[
  {
    "key": "competitor_activities",
    "title": "Wettbewerber-Aktivitäten",
    "items": [
      {
        "signal_id": "uuid",
        "company": "Acme Corp",
        "title": "Acme launcht KI-gestütztes Forecasting",
        "narrative": "Acme hat diese Woche...",
        "implication_for_us": "Das erhöht den Druck auf...",
        "movement_strength": "strong",
        "source_url": "https://acme.com/blog/...",
        "source_domain": "acme.com",          // extracted via urlparse(document.url).netloc
        "source_title": "Acme Blog – May 2025" // = source.name if available, else document.url path
      }
    ]
  }
]
```

### Updated Pydantic Schemas

New types added to `backend/app/schemas/digest.py`:

```python
class DigestSectionItem(BaseModel):
    signal_id: str
    company: str
    title: str
    narrative: str
    implication_for_us: str
    movement_strength: str
    source_url: str | None
    source_domain: str | None
    source_title: str | None

class DigestSection(BaseModel):
    key: str
    title: str
    items: list[DigestSectionItem]

class DigestRead(BaseModel):
    ...
    sections: list[DigestSection] = []  # new field
```

---

## Backend Changes

### New module: `backend/app/digester/`

| File | Responsibility |
|---|---|
| `pipeline.py` | Orchestrates full digest generation: loops sections, merges results, persists |
| `sections.py` | Section definitions: key, title, signal_type filters, assessment_class filters |
| `curator.py` | Per-section LLM call: builds prompt, calls LLM, parses structured JSON response |
| `prompts.py` | Prompt templates for section curation and intro summary |

### Updated: `backend/app/routers/digests.py`

`POST /api/digests/generate` delegates to `digester.pipeline.generate_digest()` instead of inline logic.

### LLM Call Budget

- 1 call per non-empty section (max 5)
- 1 call for intro summary
- **Max 6 LLM calls per digest generation**

---

## Frontend Changes

### `frontend/src/pages/WeeklyDigest.tsx`

- Render `sections` array instead of flat `key_signals`
- Per section: heading + divider, then items
- Per item:
  - Company badge + `movement_strength` tag (colour-coded: weak=grey, relevant=blue, strong=orange, market_shaping=red)
  - Title as clickable link (`source_url`)
  - `narrative` paragraph
  - `implication_for_us` in muted style
  - Source line: `source_domain — source_title` (plain text, visible)
- Empty sections hidden
- Falls back to legacy `key_signals` rendering if `sections` is empty (backwards compat)

### "Als E-Mail kopieren" Button

New button in digest header. On click, writes to clipboard:

```
WFM Market Intelligence — KW 19 | 5. – 11. Mai 2025

{section.title}
─────────────────────────
▸ {item.title} ({item.company})
  {item.narrative} {item.implication_for_us}
  Quelle: {item.source_domain} — {item.source_title}
  {item.source_url}

[repeated per item and section]

─────────────────────────
Vollständiger Digest: https://[VITE_APP_URL]/digest/{digest.id}
```

### Updated Types: `frontend/src/types/index.ts`

Add `DigestSectionItem`, `DigestSection` interfaces. Update `Digest` type to include `sections: DigestSection[]`.

---

## Out of Scope

- Automatic email sending (SMTP/SendGrid) — manual clipboard copy only
- Scheduling / automatic weekly generation — manual trigger only
- Per-section feedback / rating UI
- Multi-language digest output
