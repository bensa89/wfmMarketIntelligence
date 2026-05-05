# backend/app/analyser/briefing.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.company import Company
from app.models.document import Document
from app.analyser.client import call_llm


def _build_briefing_prompt(ctx: dict) -> str:
    lines = [
        "Du bist ein Market Intelligence Analyst.",
        "Erstelle eine prägnante, handlungsorientierte Zusammenfassung der wichtigsten Marktentwicklungen.",
        "",
        f"Analysezeitraum: letzte {ctx['days']} Tage",
        f"Neue Signale gesamt: {ctx['total_new']}",
        f"Davon hohe Relevanz (≥0.7): {ctx['high_relevance_count']}",
        "",
        "Aktivste Unternehmen (neue Signale):",
    ]
    for name, count in ctx["company_activity"]:
        lines.append(f"  - {name}: {count} Signale")

    lines += ["", "Top-Signale nach Relevanz:"]
    for s in ctx["top_signals"]:
        lines.append(
            f"  - [{s['company']}] {s['title']} "
            f"(Relevanz: {s['relevance']:.2f}, Typ: {s['type']})"
        )
        if s.get("source_url"):
            lines.append(f"    Quelle: {s['source_url']}")
        if s.get("why_it_matters"):
            lines.append(f"    → {s['why_it_matters']}")

    lines += ["", "Signaltyp-Verteilung:"]
    for stype, count in ctx["type_distribution"]:
        lines.append(f"  - {stype}: {count}")

    lines += [
        "",
        "Erstelle auf Deutsch:",
        "1. Kurze Zusammenfassung (2-3 Sätze) der wichtigsten Entwicklungen",
        "2. Top 3 Handlungsempfehlungen als Markdown-Tabelle mit Spalten: Priorität, Signal, Grund",
        "3. Ausblick: Was könnte sich als nächstes entwickeln?",
        "",
        "Verwende für die Empfehlungen eine saubere Markdown-Tabelle im Format:",
        "| Priorität | Signal | Grund |",
        "|-----------|--------|-------|",
        "| #1 | ... | ... |",
        "",
        "Verlinke jedes Signal in der Tabelle mit der Originalquelle als Markdown-Link:",
        "Format: [Signaltitel](Quell-URL). Nutze die unter 'Quelle:' angegebenen URLs.",
        "Beispiel: | #1 | [BAG Ruling](https://example.com/artikel) | Begründung... |",
        "",
        "Halte es prägnant und konkret.",
    ]
    return "\n".join(lines)


def generate_briefing_content(db: Session, crawl_run_id: Optional[str] = None) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    new_signals = db.query(Signal).filter(Signal.created_at >= cutoff).all()
    total_new = len(new_signals)
    high_relevance_count = sum(
        1 for s in new_signals if (s.relevance_score or 0) >= 0.7
    )

    company_activity = (
        db.query(Company.name, func.count(Signal.id).label("count"))
        .join(Signal, Signal.company_id == Company.id)
        .filter(Signal.created_at >= cutoff)
        .group_by(Company.name)
        .order_by(func.count(Signal.id).desc())
        .limit(5)
        .all()
    )

    top_signals_rows = (
        db.query(Signal, Company.name, Document.url)
        .join(Company, Company.id == Signal.company_id)
        .join(Document, Document.id == Signal.document_id)
        .filter(Signal.created_at >= cutoff)
        .order_by(Signal.relevance_score.desc().nullslast())
        .limit(10)
        .all()
    )
    top_signals = [
        {
            "title": s.title,
            "company": name,
            "relevance": s.relevance_score or 0,
            "type": s.signal_type.value,
            "why_it_matters": s.why_it_matters,
            "source_url": doc_url,
        }
        for s, name, doc_url in top_signals_rows
    ]

    type_dist = (
        db.query(Signal.signal_type, func.count(Signal.id).label("count"))
        .filter(Signal.created_at >= cutoff)
        .group_by(Signal.signal_type)
        .order_by(func.count(Signal.id).desc())
        .all()
    )
    type_distribution = [(st.value, count) for st, count in type_dist]

    ctx = {
        "days": 7,
        "total_new": total_new,
        "high_relevance_count": high_relevance_count,
        "company_activity": [(name, count) for name, count in company_activity],
        "top_signals": top_signals,
        "type_distribution": type_distribution,
    }

    prompt = _build_briefing_prompt(ctx)
    return call_llm(prompt, max_tokens=2048)
