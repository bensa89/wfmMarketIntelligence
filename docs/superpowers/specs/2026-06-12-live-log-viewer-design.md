# Live Log Viewer — Design Spec

**Date:** 2026-06-12  
**Status:** Approved

## Summary

Add a live backend log viewer to the admin area at `/admin/logs`. Logs stream in real-time via Server-Sent Events (SSE) using `fetch` + `ReadableStream` on the frontend to retain HTTP Basic Auth compatibility. Filtering by level and module happens in the frontend.

---

## Architecture

### Backend

**`LogStreamHandler`** — a custom `logging.Handler` subclass, registered into the root logger during FastAPI app lifespan startup.

Responsibilities:
- On each `emit()`, serialize the record to `{"timestamp", "level", "name", "message"}`
- Append to a global `deque(maxlen=500)` (backlog for new connections)
- Push to all active per-client `asyncio.Queue` instances (fan-out)

**`backend/app/routers/logs.py`** — new router with a single endpoint:

```
GET /api/logs/stream
```

- Protected by the existing global `Depends(verify_credentials)`
- On connect: creates a per-client `asyncio.Queue`, registers it, flushes backlog as initial SSE events
- Then yields new events from the queue as `data: <json>\n\n` SSE frames
- On disconnect (client closes connection): removes the queue from the active list
- Included in `main.py` with prefix `/api/logs`

**SSE frame format:**
```
data: {"timestamp": "2026-06-12T14:23:01.123Z", "level": "INFO", "name": "app.crawler.pipeline", "message": "Crawling https://..."}

```

### Frontend

**`frontend/src/hooks/useLogStream.ts`** — custom hook encapsulating stream logic:
- Calls `getAuthHeaders()` from `api/client.ts` (reads `localStorage('wfm_credentials')`, returns `Authorization: Basic <b64>`)
- Opens a `fetch()` with that header
- Reads `response.body` as a `ReadableStream`, decodes SSE lines, parses JSON
- Maintains local buffer of up to 1000 log entries (drops oldest on overflow)
- Exposes: `{ logs, status, pause, resume, clear, reconnect }`
- Auto-reconnect: waits 2s on disconnect, retries up to 5 times, then sets status to `error`

**`frontend/src/pages/LogsAdmin.tsx`** — new page at `/admin/logs`:

Layout (consistent with `ScheduleAdmin` — uses existing `SectionCard`):
- **Filter bar**: Level dropdown (ALL / DEBUG / INFO / WARNING / ERROR), Module dropdown (populated dynamically from received log `name` fields), Pause/Resume toggle, Clear button
- **Log panel**: monospace, dark background (`bg-slate-900 text-slate-100`), color-coded levels:
  - DEBUG → `text-slate-400`
  - INFO → `text-blue-300`
  - WARNING → `text-yellow-300`
  - ERROR → `text-red-400`
- Auto-scroll to bottom unless user has manually scrolled up (detect via scroll event)
- Connection status badge (Verbunden / Getrennt / Fehler)

**`App.tsx`** — add route `<Route path="admin/logs" element={<LogsAdmin />} />`

**`Layout.tsx` / sidebar** — add navigation entry "Logs" in the admin section.

---

## Data Flow

```
Python logger.info(...)
  → LogStreamHandler.emit()
    → deque (backlog)
    → asyncio.Queue × N (one per active SSE client)
      → GET /api/logs/stream (SSE)
        → fetch() + ReadableStream (frontend hook)
          → local buffer (max 1000)
            → filtered view in LogsAdmin.tsx
```

---

## Edge Cases

| Scenario | Handling |
|---|---|
| Client disconnects | Queue removed from active list; generator exits cleanly |
| No active clients | Records still written to backlog; no overhead |
| Reconnect | Backlog (last 500 lines) sent immediately on reconnect |
| Auto-reconnect failure (>5 attempts) | Status → `error`, manual retry button shown |
| Frontend buffer overflow | Oldest 100 entries dropped when buffer exceeds 1000 |
| Test environment | `LogStreamHandler` only registered in lifespan, not in test fixtures — no impact |

---

## Files Changed

| File | Action |
|---|---|
| `backend/app/log_stream.py` | **New** — `LogStreamHandler`, global deque + queue registry |
| `backend/app/routers/logs.py` | **New** — SSE router |
| `backend/app/main.py` | **Modify** — import `log_stream` in lifespan, include logs router |
| `frontend/src/hooks/useLogStream.ts` | **New** — SSE stream hook |
| `frontend/src/pages/LogsAdmin.tsx` | **New** — log viewer page |
| `frontend/src/App.tsx` | **Modify** — add `/admin/logs` route |
| `frontend/src/components/Layout.tsx` | **Modify** — add "Logs" nav entry |

---

## Out of Scope

- Log persistence to database
- Log export / download
- Log level configuration via UI
- Multi-instance / distributed log aggregation
