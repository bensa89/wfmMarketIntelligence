# Signal Assessment Detail — Drawer zu Modal

**Date:** 2026-05-18
**Status:** Approved for implementation

---

## 1. Kontext und Ziel

Auf `/signals` wird das Assessment-Detail derzeit als rechtes Seitenpanel (Drawer, 480px) angezeigt. Der Platz ist eng für die enthaltenen Informationen (11 Sektionen). Ziel ist es, das Panel in ein zentriertes Modal umzuwandeln — analog zum Signal-Detail-Modal auf dem Dashboard.

---

## 2. Architekturentscheidung

**Option A gewählt:** `SignalDetailDrawer.tsx` wird in-place umgebaut. Props-Schnittstelle, Inhalt und Komponentenname bleiben unverändert. Nur das Layout ändert sich.

Begründung: Kein Refactoring der Aufrufer nötig. Die Scorecard-Spec referenziert `SignalDetailDrawer` namentlich — der Name bleibt erhalten.

**Scope:** Ausschließlich `frontend/src/components/signals/SignalDetailDrawer.tsx`. Keine Änderungen an Aufrufer-Dateien.

---

## 3. Layout-Änderungen

| Element | Vorher (Drawer) | Nachher (Modal) |
|---|---|---|
| Backdrop | `fixed inset-0 bg-black/50 z-40` | `fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4` |
| Container | `fixed right-0 top-0 h-full w-[480px] z-50` | `bg-white rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col` |
| Scroll | ganzer Container scrollt | nur Content-Bereich scrollt, Header sticky |
| Animation | slide-in von rechts (`translate-x`) | entfernt (oder einfaches fade-in) |

---

## 4. Was unverändert bleibt

- Props: `item: SignalFeedItem`, `onClose: () => void`
- Alle 11 Inhaltssektionen (Movement, Summary, Why It Matters, Capabilities, Assessment Summary, Implication, Strategic Intent, Watch Items, Gameplay Tags, Source, Generate-Button)
- Schließverhalten: Backdrop-Click, Escape-Key, Close-Button
- Komponentenname `SignalDetailDrawer` und Dateiname `SignalDetailDrawer.tsx`

---

## 5. Betroffene Dateien

- `frontend/src/components/signals/SignalDetailDrawer.tsx` — wird geändert
- Keine weiteren Dateien
