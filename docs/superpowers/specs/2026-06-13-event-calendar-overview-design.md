# Event Calendar on Overview Page

**Date:** 2026-06-13  
**Status:** Approved

## Goal

Add an Event Calendar section to the Overview page (`/overview`) that shows:
- **Upcoming events**: Future industry events where competitors plan to appear, sorted chronologically
- **Past events (last 30 days)**: Events that recently took place, with which competitors attended

## Data Model

Two new nullable columns on the existing `signals` table:

```python
event_date     = Column(DateTime, nullable=True)   # When the event takes place
event_location = Column(String(255), nullable=True) # e.g. "Las Vegas", "Amsterdam"
```

**Migration:** Single Alembic migration adds both columns. Existing rows remain NULL.

**Population:** The LLM analyser extracts `event_date` and `event_location` only when `signal_type = event_or_thought_leadership`. Thought-leadership articles without a specific event date get `event_date: null`. Signals with `event_date IS NOT NULL` are treated as events.

**No signal type split:** `event_or_thought_leadership` remains as-is. The implicit distinction (event_date set vs. null) is sufficient for filtering.

## Analyser Prompt Update

`backend/app/analyser/prompts.py` — extend the JSON schema in `build_analysis_prompt` with two new optional fields:

```json
"event_date": "ISO-8601 date of the event itself (not publication date), or null if not an event",
"event_location": "City or venue of the event, or null"
```

The instruction clarifies: these fields are only meaningful for `event_or_thought_leadership` signals describing a specific upcoming or recent event.

## Backend API

**New endpoint:** `GET /api/intelligence/events`  
**Router:** `backend/app/routers/intelligence.py` (existing router, new route)

### Query logic

1. Fetch all signals where `signal_type = event_or_thought_leadership` AND `event_date IS NOT NULL`
2. Split into two buckets:
   - **upcoming**: `event_date >= today`
   - **past**: `today - 30 days <= event_date < today`
3. Group signals by event: signals sharing the same `event_date` and a matching `title` (case-insensitive, trimmed) are merged into one event entry with multiple attendees.
4. Sort upcoming ascending by `event_date`, past descending by `event_date`.

### Response schema

```json
{
  "upcoming": [
    {
      "event_date": "2026-09-15",
      "event_location": "Las Vegas",
      "title": "WFM World Summit 2026",
      "attendees": [
        { "company_id": "...", "company_name": "Competitor A", "signal_id": "..." }
      ]
    }
  ],
  "past": [
    {
      "event_date": "2026-06-05",
      "event_location": "Paris",
      "title": "Unleash World Paris",
      "attendees": [
        { "company_id": "...", "company_name": "Competitor A", "signal_id": "..." },
        { "company_id": "...", "company_name": "Competitor B", "signal_id": "..." }
      ]
    }
  ]
}
```

No Pydantic response_model needed initially — `dict` return is consistent with the existing `/intelligence/overview` endpoint pattern.

## Frontend

### Hook

New `useEventCalendar()` hook in `frontend/src/hooks/useEventCalendar.ts`:

```ts
export function useEventCalendar() {
  return useQuery({
    queryKey: ['intelligence', 'events'],
    queryFn: () => apiGet<EventCalendarResponse>('/intelligence/events'),
    staleTime: 5 * 60 * 1000,
  });
}
```

New type `EventCalendarResponse` added to `frontend/src/types/intelligence.ts`.

### Component

New `EventTimelinePanel` in `frontend/src/components/overview/EventTimelinePanel.tsx`:

- Vertical timeline with a "Heute" marker at the current date
- **Upcoming events** (above / below today marker, blue): event date, title, location, competitor badges per attendee
- **Past events** (below, greyed out): same structure but muted colours
- Clicking an event entry opens `SignalDetailDrawer` with the attendee signal with the highest `relevance_score` (ties broken by `created_at` descending)
- Empty state: "Keine Events gefunden" message

### Overview page integration

`frontend/src/pages/OverviewPage.tsx` — add a full-width row below the existing `grid-cols-2` block:

```tsx
<div className="mb-4">
  <EventTimelinePanel />
</div>
```

## Out of Scope

- Deduplication of events across companies by fuzzy title matching (keep exact match only for now)
- Manual event entry (admin UI)
- Notifications / reminders for upcoming events
- Backfilling existing signals with event_date via re-analysis
