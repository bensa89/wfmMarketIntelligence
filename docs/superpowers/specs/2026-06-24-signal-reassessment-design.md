# Signal Re-Assessment with Optional Analyst Note

**Date:** 2026-06-24
**Status:** Approved

## Goal

`SignalDetailDrawer` currently only offers a "Generate Assessment" button when a signal has no assessment yet (`!a`). Once an assessment exists, there is no way to re-run it. Add the ability to re-run the LLM assessment for a signal at any time, optionally with a short analyst-supplied note that the LLM should weight when assessing — e.g. "the pricing angle here matters more than usual."

## What changes

### Backend

- **`backend/app/models/signal_assessment.py`**: add `user_note = Column(Text, nullable=True)` to `SignalAssessment`.
- **Alembic migration**: add nullable `user_note` column to `signal_assessments`.
- **`backend/app/assessor/prompts.py`**: `build_assessment_prompt()` gets an optional `user_note: str | None = None` parameter. When set, append a clearly delimited section to the prompt, e.g.:
  ```
  Additional guidance from the analyst — give this special weight in your assessment:
  "{user_note}"
  ```
  `build_self_assessment_prompt()` is unaffected (self-assessment is not triggered from this UI).
- **`backend/app/assessor/pipeline.py`**: `assess_signal(signal, db, user_note: str | None = None)` passes `user_note` into the prompt builder and persists it on the `SignalAssessment` row, both on the create path and the existing-row update path.
- **`backend/app/routers/intelligence.py`**:
  - `_assessment_to_dict()` includes `"user_note": a.user_note`.
  - `trigger_assess_signal` accepts an optional request body (`AssessSignalRequest { user_note: Optional[str] = None }` in `backend/app/schemas/signal_assessment.py`), defaulting to no body so existing callers keep working. The note (if present) is passed through to `assess_signal`.
- **`backend/app/schemas/signal_assessment.py`**: add `user_note: Optional[str] = None` to `SignalAssessmentRead` for consistency, and add the new `AssessSignalRequest` model.

### Frontend

- **`frontend/src/types/intelligence.ts`**: `SignalAssessment.user_note: string | null`.
- **`frontend/src/hooks/useAssessSignal.ts`**: mutation input changes from `signalId: string` to `{ signalId: string; userNote?: string }`; POST body becomes `{ user_note: userNote }`.
- **`frontend/src/components/signals/SignalDetailDrawer.tsx`**:
  - The existing `{!a && <button>Generate Assessment</button>}` block is replaced by an always-visible trigger, labeled "Assessment generieren" when `!a` and "Assessment neu durchführen" when `a` exists.
  - Clicking it expands an inline form: a textarea (pre-filled with `a?.user_note ?? ''`) plus "Ausführen" / "Abbrechen" buttons. Leaving the textarea empty re-runs the assessment without a note (same as today's plain re-run).
  - Confirming calls `assess.mutate({ signalId: item.id, userNote: note || undefined })` and collapses the form on success.

## What stays the same

- Re-assessment overwrites the existing `SignalAssessment` row in place — no history/versioning is introduced (matches current behavior for first-time assessment).
- `assess_signal_self` and the automated self-assessment path used during crawling are untouched.
- All other assessment fields, scoring logic (`compute_movement_score`, `DimensionRouter`, benchmark/scorecard recompute side effects) are unchanged.
- The drawer's layout, the "Rohdokument" section, and all other sections are unaffected.

## Out of scope

- Assessment history/versioning (showing past assessments or past notes over time).
- Allowing notes on the automated self-assessment pipeline.
- Bulk re-assessment of multiple signals at once.
