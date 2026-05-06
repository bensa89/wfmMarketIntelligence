# Per-Source Discovery Depth — Design Spec

**Date:** 2026-05-06  
**Status:** Approved

## Overview

Add a per-source `discovery_depth` override that supersedes the global `DISCOVERY_DEPTH` env setting. Sources with `null` fall back to the global default, preserving existing behavior without migration changes.

## Approach

Optional override (`null` = use global default). Chosen over a mandatory field to avoid breaking existing sources and to keep the global env setting meaningful as a true default.

## Backend

### Model (`backend/app/models/source.py`)
Add nullable integer column:
```python
discovery_depth = Column(Integer, nullable=True, default=None)
```

### Schemas (`backend/app/schemas/source.py`)
- `SourceCreate`: `discovery_depth: Optional[int] = None`
- `SourceUpdate`: `discovery_depth: Optional[int] = None`
- `SourceRead`: `discovery_depth: Optional[int]`

### Discovery Pipeline (`backend/app/crawler/discovery.py`)
Replace all reads of `settings.discovery_depth` with:
```python
effective_depth = source.discovery_depth if source.discovery_depth is not None else settings.discovery_depth
```
Use `effective_depth` for the zero-check (skip discovery) and the depth-limit guard.

### Alembic Migration
New revision: `ALTER TABLE sources ADD COLUMN discovery_depth INTEGER NULL`

## Frontend

### Types (`frontend/src/types/index.ts`)
Add to `Source` interface: `discovery_depth: number | null`

### Edit Modal (`frontend/src/pages/SourcesAdmin.tsx`)
- New state: `editDiscoveryDepth: number | null`
- Populated in `openEditModal` from `source.discovery_depth`
- Reset in `closeEditModal` to `null`
- Field in form: number input, min=0, max=5, step=1, empty value = `null`
- Hint: "0 = Discovery deaktiviert, leer = globaler Standard"
- Included in `updates` object when value changed, sent via `updateSource.mutate`

## Constraints
- Valid values: 0 (disable discovery for this source) to 5
- `null` means "inherit global default" — never stored as 0 implicitly
- No changes to the "Add Source" form (new sources always start with `null`)
- No changes to `_MAX_PAGES_PER_RUN` (still global)
