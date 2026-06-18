# Event Calendar Panel: Timeline → List

**Date:** 2026-06-18
**Status:** Approved

## Goal

`EventTimelinePanel` (used both on the Dashboard and the dedicated `/events` page via `EventCalendarPage`) currently renders events as a vertical timeline: an absolute connecting line, a colored dot per row, and a `pl-[77px]` wrapper offset that exists purely to position that line. This reserves a wide, mostly-empty strip on the left of the panel.

Rework it into a plain list. All information shown today must remain — only the timeline scaffolding (line, dots, the padding hack) is removed.

## What changes

In `frontend/src/components/overview/EventTimelinePanel.tsx`:

- Remove the absolute vertical line (`<div className="absolute left-[77px] ... bg-slate-100" />`).
- Remove the per-row dot (`EventRow`'s "Dot" block).
- Remove the `pl-[77px]` wrapper around the row list, and the matching `-ml-[77px] pl-[85px]` counter-offset on the "Vergangene Events" section header — both existed only to align content with the line.
- Replace the "Heute" timeline marker (colored dot + line) with a plain section divider: a thin horizontal rule with "Heute · {current date}" as a centered or left-aligned label, sitting between the past and upcoming groups.

## What stays the same

- Row content and order: date (formatted `12. Jän 2026`) + relative-days label (`Heute` / `Morgen` / `in X Tagen` / `vor X Tagen`) in a compact column, immediately followed by attendee logos + company names, event title, "Neu" badge, event-type badge, and location — same two-part row shape (date column, then content), just without the dot in between.
- Past-event dimming (`opacity-55` / muted text colors).
- The collapse/expand toggle for past events in full view (`pastExpanded`, `PAST_COLLAPSED_LIMIT`).
- Click-to-open behavior: clicking a row opens `SignalDetailDrawer` for the top attendee's signal.
- The `fullView` vs. compact-dashboard behavior (30-day upcoming filter, "Alle Events ansehen" footer link).
- `useEventCalendar` hook, `EventCalendarPage`, and all backend/API/data — unaffected, this is a presentational change only.

## Out of scope

- Changing what data is fetched or how events are grouped/deduplicated server-side.
- Changing the Dashboard or `/events` page layout beyond the panel's internals.
- Redesigning the date/content split into a single inline line (considered and rejected — current two-part row style is kept).
